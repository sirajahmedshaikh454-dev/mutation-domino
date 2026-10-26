from __future__ import annotations

import httpx
import pytest
import respx

from app.core.config import Settings
from app.domain.errors import RateLimited, StructureTooLarge, UpstreamError, UpstreamTimeout
from app.integrations.http import BoundedHttpClient, validate_upstream_url


def settings(tmp_path, **overrides) -> Settings:
    return Settings(
        cache_dir=tmp_path / "cache",
        max_metadata_bytes=1024,
        max_structure_bytes=4096,
        **overrides,
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://rest.uniprot.org/uniprotkb/P69905.json",
        "https://evil.example.com/file.cif",
        "https://user:pass@rest.uniprot.org/x",
        "https://rest.uniprot.org:8443/x",
    ],
)
def test_url_allowlist(url: str) -> None:
    with pytest.raises(UpstreamError):
        validate_upstream_url(url, {"rest.uniprot.org"})


def test_allowed_url() -> None:
    assert (
        validate_upstream_url("https://rest.uniprot.org/uniprotkb/P69905.json", {"rest.uniprot.org"})
        == "https://rest.uniprot.org/uniprotkb/P69905.json"
    )


async def test_rejects_redirect(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/x").mock(
            return_value=httpx.Response(302, headers={"location": "https://evil.example.com"})
        )
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(UpstreamError, match="redirect"):
                await client.get_json("https://rest.uniprot.org/x", allowed_hosts={"rest.uniprot.org"})


async def test_rate_limit(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/x").mock(return_value=httpx.Response(429))
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(RateLimited):
                await client.get_json("https://rest.uniprot.org/x", allowed_hosts={"rest.uniprot.org"})


async def test_timeout(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/x").mock(side_effect=httpx.ConnectTimeout("boom"))
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(UpstreamTimeout):
                await client.get_json("https://rest.uniprot.org/x", allowed_hosts={"rest.uniprot.org"})


async def test_content_length_limit(tmp_path) -> None:
    with respx.mock:
        respx.get("https://alphafold.ebi.ac.uk/big.cif").mock(
            return_value=httpx.Response(
                200,
                content=b"data_x\n" * 1000,
                headers={"content-length": "999999", "content-type": "chemical/x-mmcif"},
            )
        )
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(StructureTooLarge):
                await client.get_bytes(
                    "https://alphafold.ebi.ac.uk/big.cif",
                    allowed_hosts={"alphafold.ebi.ac.uk"},
                )


async def test_malformed_json(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/x").mock(
            return_value=httpx.Response(
                200, content=b"{not json", headers={"content-type": "application/json"}
            )
        )
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(UpstreamError, match="malformed"):
                await client.get_json("https://rest.uniprot.org/x", allowed_hosts={"rest.uniprot.org"})


async def test_unexpected_content_type(tmp_path) -> None:
    with respx.mock:
        respx.get("https://rest.uniprot.org/x").mock(
            return_value=httpx.Response(200, content=b"<html>", headers={"content-type": "text/html"})
        )
        async with BoundedHttpClient(settings(tmp_path), retries=0) as client:
            with pytest.raises(UpstreamError, match="content type"):
                await client.get_json("https://rest.uniprot.org/x", allowed_hosts={"rest.uniprot.org"})
