from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.time import utc_now_iso
from app.domain.errors import MalformedStructure, StructureUnavailable, UpstreamError
from app.domain.models import ProteinInfo, StructureInfo
from app.domain.structure import ParsedStructure, parse_structure_file
from app.domain.variant import normalize_accession
from app.integrations.alphafold import AlphaFoldAdapter, AlphaFoldArtifact
from app.integrations.cache import DiskCache
from app.integrations.fixtures import FixtureProvider
from app.integrations.http import BoundedHttpClient
from app.integrations.uniprot import UniProtAdapter, protein_info_from_payload

logger = get_logger(__name__)
SAFE_VERSION = re.compile(r"[^A-Za-z0-9._-]")


@dataclass
class ProteinBundle:
    protein: ProteinInfo
    structure: ParsedStructure
    structure_info: StructureInfo
    structure_path: Path
    alphafold_metadata: dict[str, Any]


def _structure_key(accession: str, version: str) -> str:
    return f"af_{accession}_{SAFE_VERSION.sub('_', version)}"


def _is_fresh(retrieved_at: str, ttl_seconds: int) -> bool:
    if ttl_seconds <= 0:
        return False
    try:
        timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(UTC) - timestamp < timedelta(seconds=ttl_seconds)


class ProteinService:
    def __init__(
        self,
        settings: Settings,
        *,
        cache: DiskCache | None = None,
        fixture_provider: FixtureProvider | None = None,
    ) -> None:
        self.settings = settings
        self.cache = cache or DiskCache(settings.cache_dir, settings.max_cache_bytes)
        self.fixtures = fixture_provider or FixtureProvider(settings.offline_fixture_dir)

    @property
    def is_fixture_mode(self) -> bool:
        return self.settings.mode == "fixture"

    async def load(self, raw_accession: str) -> ProteinBundle:
        accession = normalize_accession(raw_accession)
        if self.is_fixture_mode:
            return self._load_fixture(accession)
        async with BoundedHttpClient(self.settings) as client:
            protein = await self._get_protein(client, accession)
            metadata = await self._get_alphafold_metadata(client, accession)
            artifact = await self._get_structure(client, accession, metadata)
        return self._finalise(protein, artifact)

    def _load_fixture(self, accession: str) -> ProteinBundle:
        protein = self.fixtures.protein(accession)
        artifact = self.fixtures.structure(accession)
        fixture_path = self.fixtures.fixture_dir / f"af_{accession}.cif"
        structure = self._parse(fixture_path, artifact.structure_info)
        return ProteinBundle(
            protein=protein,
            structure=structure,
            structure_info=artifact.structure_info,
            structure_path=fixture_path,
            alphafold_metadata=artifact.metadata,
        )

    async def _get_protein(self, client: BoundedHttpClient, accession: str) -> ProteinInfo:
        key = f"uniprot_{accession}"
        cached = self.cache.read_json(key)
        if isinstance(cached, dict):
            retrieved_at = str(cached.get("retrieved_at") or "")
            payload = cached.get("payload")
            if payload and _is_fresh(retrieved_at, self.settings.cache_ttl_seconds):
                try:
                    return protein_info_from_payload(
                        payload,
                        source_url=str(cached.get("source_url") or ""),
                        retrieved_at=retrieved_at,
                        mode="live",
                    )
                except UpstreamError:
                    logger.warning("Ignoring invalid cached UniProt payload for %s", accession)
        adapter = UniProtAdapter(
            client,
            self.settings.uniprot_base_url,
            max_length=self.settings.max_protein_length,
        )
        payload, source_url = await adapter.fetch_payload(accession)
        protein = protein_info_from_payload(payload, source_url=source_url)
        if protein.accession != accession:
            raise UpstreamError(
                "UniProt returned a different primary accession than requested.",
                details={"requested": accession, "returned": protein.accession},
            )
        if protein.length > self.settings.max_protein_length:
            raise UpstreamError(
                "The protein exceeds the configured length limit.",
                details={"length": protein.length, "limit": self.settings.max_protein_length},
            )
        self.cache.put_json(
            key,
            {
                "retrieved_at": protein.retrieved_at,
                "source_url": protein.source_url,
                "payload": payload,
            },
        )
        return protein

    async def _get_alphafold_metadata(self, client: BoundedHttpClient, accession: str) -> dict[str, Any]:
        key = f"alphafold_{accession}"
        cached = self.cache.read_json(key)
        if isinstance(cached, dict):
            entry = cached.get("entry")
            retrieved_at = str(cached.get("retrieved_at") or "")
            if isinstance(entry, dict) and _is_fresh(retrieved_at, self.settings.cache_ttl_seconds):
                return entry
        try:
            adapter = AlphaFoldAdapter(client, self.settings.alphafold_base_url)
            entry = await adapter.fetch_metadata(accession)
        except StructureUnavailable:
            raise
        self.cache.put_json(key, {"retrieved_at": utc_now_iso(), "entry": entry})
        return entry

    async def _get_structure(
        self,
        client: BoundedHttpClient,
        accession: str,
        entry: dict[str, Any],
    ) -> AlphaFoldArtifact:
        latest = entry.get("latestVersion")
        version = f"v{latest}" if latest is not None else "unknown"
        key = _structure_key(accession, version)
        suffix = ".cif" if entry.get("cifUrl") else ".pdb"
        cached_path = self.cache.path_for(key, suffix)
        cached_meta = self.cache.read_json(f"{key}_meta")
        if cached_path.is_file() and isinstance(cached_meta, dict):
            payload = cached_path.read_bytes()
            cached_info = cached_meta.get("structure_info")
            if isinstance(cached_info, dict):
                try:
                    info = StructureInfo(**cached_info)
                    if hashlib.sha256(payload).hexdigest() == info.checksum_sha256:
                        return AlphaFoldArtifact(
                            payload=payload,
                            structure_info=info,
                            suffix=suffix,
                            metadata=entry,
                        )
                    logger.warning("Cached structure checksum mismatch for %s; refetching", accession)
                except (TypeError, ValueError):
                    logger.warning("Ignoring invalid cached structure metadata for %s", accession)
        adapter = AlphaFoldAdapter(client, self.settings.alphafold_base_url)
        artifact = await adapter.download(accession, entry)
        self.cache.put_bytes(key, artifact.payload, artifact.suffix)
        self.cache.put_json(f"{key}_meta", {"structure_info": artifact.structure_info.to_dict()})
        return artifact

    def _finalise(self, protein: ProteinInfo, artifact: AlphaFoldArtifact) -> ProteinBundle:
        suffix = artifact.suffix
        key = _structure_key(protein.accession, artifact.structure_info.model_version)
        path = self.cache.path_for(key, suffix)
        if not path.is_file():
            self.cache.put_bytes(key, artifact.payload, suffix)
        structure = self._parse(path, artifact.structure_info)
        return ProteinBundle(
            protein=protein,
            structure=structure,
            structure_info=artifact.structure_info,
            structure_path=path,
            alphafold_metadata=artifact.metadata,
        )

    def _parse(self, path: Path, info: StructureInfo) -> ParsedStructure:
        try:
            return parse_structure_file(
                path,
                chain_id=info.chain,
                source="alphafold" if info.is_predicted else "experimental",
                max_bytes=self.settings.max_structure_bytes,
                max_residues=self.settings.max_structure_residues,
            )
        except MalformedStructure:
            if path.parent == self.cache.root:
                path.unlink(missing_ok=True)
            raise

    def structure_download_name(self, accession: str, info: StructureInfo) -> str:
        return f"{accession}_{info.model_version}{'.cif' if info.file_format == 'cif' else '.pdb'}"
