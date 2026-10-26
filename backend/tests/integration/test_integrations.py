from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest
import respx

from app.core.config import Settings
from app.domain.errors import ProteinNotFound, StructureUnavailable
from app.integrations.alphafold import AlphaFoldAdapter
from app.integrations.cache import DiskCache
from app.integrations.http import BoundedHttpClient
from app.integrations.uniprot import UniProtAdapter
from app.services.proteins import ProteinService

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/P69905.json"
ALPHAFOLD_API = "https://alphafold.ebi.ac.uk/api/prediction/P69905"
CIF_URL = "https://alphafold.ebi.ac.uk/files/AF-P69905-F1-model_v6.cif"


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        mode="live",
        cache_dir=tmp_path / "cache",
        offline_fixture_dir=FIXTURES,
        cache_ttl_seconds=3600,
    )


def uniprot_bytes() -> bytes:
    return (FIXTURES / "uniprot_P69905.json").read_bytes()


def alphafold_bytes() -> bytes:
    return (FIXTURES / "alphafold_P69905.json").read_bytes()


def cif_bytes() -> bytes:
    return (FIXTURES / "af_P69905.cif").read_bytes()


def routes() -> tuple[respx.Route, respx.Route, respx.Route]:
    return (
        respx.get(UNIPROT_URL).mock(
            return_value=httpx.Response(
                200, content=uniprot_bytes(), headers={"content-type": "application/json"}
            )
        ),
        respx.get(ALPHAFOLD_API).mock(
            return_value=httpx.Response(
                200, content=alphafold_bytes(), headers={"content-type": "application/json"}
            )
        ),
        respx.get(CIF_URL).mock(
            return_value=httpx.Response(
                200, content=cif_bytes(), headers={"content-type": "chemical/x-mmcif"}
            )
        ),
    )


async def test_uniprot_adapter(tmp_path) -> None:
    with respx.mock:
        routes()
        async with BoundedHttpClient(make_settings(tmp_path), retries=0) as client:
            adapter = UniProtAdapter(client, "https://rest.uniprot.org", max_length=4000)
            protein = await adapter.fetch("P69905")
    assert protein.accession == "P69905"
    assert protein.name == "Hemoglobin subunit alpha"
    assert protein.length == 142
    assert protein.sequence.startswith("MVLSPADK")
    assert protein.gene == "HBA1"
    assert protein.source_url == UNIPROT_URL


async def test_uniprot_adapter_404(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/uniprotkb/Q00000.json").mock(return_value=httpx.Response(404))
        async with BoundedHttpClient(make_settings(tmp_path), retries=0) as client:
            adapter = UniProtAdapter(client, "https://rest.uniprot.org", max_length=4000)
            with pytest.raises(ProteinNotFound):
                await adapter.fetch("Q00000")


async def test_alphafold_adapter(tmp_path) -> None:
    with respx.mock:
        routes()
        async with BoundedHttpClient(make_settings(tmp_path), retries=0) as client:
            adapter = AlphaFoldAdapter(client, "https://alphafold.ebi.ac.uk")
            entry = await adapter.fetch_metadata("P69905")
            artifact = await adapter.download("P69905", entry)
    assert artifact.suffix == ".cif"
    assert artifact.structure_info.model_version == "v6"
    assert artifact.structure_info.chain == "A"
    assert artifact.structure_info.checksum_sha256 == hashlib.sha256(cif_bytes()).hexdigest()
    assert artifact.payload == cif_bytes()


async def test_alphafold_adapter_unavailable(tmp_path) -> None:
    with respx.mock:
        respx.get(ALPHAFOLD_API).mock(return_value=httpx.Response(404))
        async with BoundedHttpClient(make_settings(tmp_path), retries=0) as client:
            adapter = AlphaFoldAdapter(client, "https://alphafold.ebi.ac.uk")
            with pytest.raises(StructureUnavailable):
                await adapter.fetch_metadata("P69905")


async def test_alphafold_rejects_html(tmp_path) -> None:
    with respx.mock:
        respx.get(ALPHAFOLD_API).mock(
            return_value=httpx.Response(
                200, content=alphafold_bytes(), headers={"content-type": "application/json"}
            )
        )
        respx.get(CIF_URL).mock(
            return_value=httpx.Response(
                200, content=b"<html>error</html>", headers={"content-type": "text/html"}
            )
        )
        async with BoundedHttpClient(make_settings(tmp_path), retries=0) as client:
            adapter = AlphaFoldAdapter(client, "https://alphafold.ebi.ac.uk")
            entry = await adapter.fetch_metadata("P69905")
            with pytest.raises(Exception, match=r"content type|not valid"):
                await adapter.download("P69905", entry)


async def test_protein_service_live_and_cache(tmp_path) -> None:
    with respx.mock:
        uniprot_route, af_route, cif_route = routes()
        service = ProteinService(make_settings(tmp_path))
        bundle = await service.load("P69905")
        assert bundle.protein.accession == "P69905"
        assert len(bundle.structure.residues) == 142
        assert bundle.structure_info.is_predicted is True
        assert bundle.structure_path.is_file()
        assert uniprot_route.call_count == 1
        assert af_route.call_count == 1
        assert cif_route.call_count == 1

        cached_bundle = await service.load("p69905")
        assert cached_bundle.protein.sequence == bundle.protein.sequence
        assert uniprot_route.call_count == 1
        assert af_route.call_count == 1
        assert cif_route.call_count == 1


async def test_protein_service_fixture_mode(tmp_path) -> None:
    settings = Settings(
        mode="fixture",
        cache_dir=tmp_path / "cache",
        offline_fixture_dir=FIXTURES,
    )
    service = ProteinService(settings)
    bundle = await service.load("P69905")
    assert bundle.protein.mode == "fixture"
    assert bundle.structure_info.mode == "fixture"
    assert len(bundle.structure.residues) == 142
    with pytest.raises(ProteinNotFound, match="Fixture mode"):
        await service.load("P12345")


def test_cache_rejects_unsafe_keys(tmp_path) -> None:
    cache = DiskCache(tmp_path / "cache", 1024)
    with pytest.raises(Exception, match="Unsafe"):
        cache.put_bytes("../escape", b"data", ".bin")
    entry = cache.put_bytes("safe_key", b"data", ".bin")
    assert entry.sha256 == hashlib.sha256(b"data").hexdigest()
    assert cache.read_bytes("safe_key", ".bin") == b"data"
    cache.put_json("meta", {"a": 1})
    assert cache.read_json("meta") == {"a": 1}


def test_cache_prunes_oldest(tmp_path) -> None:
    cache = DiskCache(tmp_path / "cache", 100)
    cache.put_bytes("first", b"a" * 60, ".bin")
    cache.put_bytes("second", b"b" * 60, ".bin")
    assert not cache.path_for("first", ".bin").exists()
    assert cache.path_for("second", ".bin").exists()
    assert cache.total_bytes() <= 100


def test_fixture_json_is_valid() -> None:
    payload = json.loads(alphafold_bytes())
    assert payload[0]["uniprotAccession"] == "P69905"
    assert payload[0]["cifUrl"] == CIF_URL
