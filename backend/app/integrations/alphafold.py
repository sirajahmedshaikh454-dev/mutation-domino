from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.core.time import utc_now_iso
from app.domain.errors import StructureUnavailable, UpstreamError
from app.domain.models import StructureInfo
from app.integrations.http import BoundedHttpClient, UpstreamStatusError, validate_upstream_url

DEFAULT_ALPHAFOLD_HOSTS = ("alphafold.ebi.ac.uk",)


@dataclass(frozen=True)
class AlphaFoldArtifact:
    payload: bytes
    structure_info: StructureInfo
    suffix: str
    metadata: dict[str, Any]


def _select_entry(payload: object, accession: str) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        raise StructureUnavailable(
            f"AlphaFold DB has no predicted model for {accession}.",
            details={"accession": accession},
        )
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("uniprotAccession") or "").upper() == accession:
            return entry
    raise StructureUnavailable(
        "AlphaFold DB returned metadata that does not match the requested accession.",
        details={"accession": accession},
    )


def _version_label(entry: dict[str, Any]) -> str:
    version = entry.get("latestVersion") or entry.get("modelVersion")
    if version is not None:
        return f"v{version}"
    entry_id = str(entry.get("entryId") or "")
    if "_v" in entry_id:
        return f"v{entry_id.rsplit('_v', 1)[1]}"
    return "unknown"


def _validate_structure_payload(payload: bytes, suffix: str) -> None:
    if len(payload) < 20:
        raise UpstreamError("AlphaFold returned an empty or truncated structure file.")
    head = payload[:2000].lstrip()
    if head.startswith(b"<"):
        raise UpstreamError("AlphaFold returned HTML instead of a structure file.")
    if suffix == ".cif" and not (head.startswith(b"data_") or b"_atom_site." in payload[:200000]):
        raise UpstreamError("AlphaFold returned a file that is not valid mmCIF.")
    if suffix == ".pdb" and not (head.startswith(b"ATOM") or head.startswith(b"HEADER")):
        raise UpstreamError("AlphaFold returned a file that is not valid PDB.")


class AlphaFoldAdapter:
    def __init__(
        self,
        client: BoundedHttpClient,
        base_url: str,
        *,
        allowed_hosts: tuple[str, ...] = DEFAULT_ALPHAFOLD_HOSTS,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._allowed_hosts = allowed_hosts
        host = urlsplit(self._base_url).hostname
        if not host or host.lower() not in {h.lower() for h in allowed_hosts}:
            raise ValueError("AlphaFold base URL host is not on the allowlist.")

    async def fetch_metadata(self, accession: str) -> dict[str, Any]:
        url = f"{self._base_url}/api/prediction/{accession}"
        try:
            payload = await self._client.get_json(url, allowed_hosts=self._allowed_hosts)
        except UpstreamStatusError as exc:
            if exc.status_code == 404:
                raise StructureUnavailable(
                    f"AlphaFold DB has no predicted model for {accession}.",
                    details={"accession": accession},
                ) from exc
            raise
        entry = _select_entry(payload, accession)
        return entry

    async def download(self, accession: str, entry: dict[str, Any]) -> AlphaFoldArtifact:
        cif_url = entry.get("cifUrl")
        pdb_url = entry.get("pdbUrl")
        if cif_url:
            url, suffix = str(cif_url), ".cif"
        elif pdb_url:
            url, suffix = str(pdb_url), ".pdb"
        else:
            raise StructureUnavailable(
                "AlphaFold metadata did not include a downloadable structure URL.",
                details={"accession": accession},
            )
        validate_upstream_url(url, self._allowed_hosts)
        payload, content_type = await self._client.get_bytes(
            url,
            allowed_hosts=self._allowed_hosts,
            accept="chemical/x-mmcif, chemical/x-pdb, application/octet-stream, text/plain",
        )
        if content_type and content_type not in {
            "chemical/x-mmcif",
            "chemical/x-pdb",
            "application/octet-stream",
            "text/plain",
            "application/x-gzip",
        }:
            raise UpstreamError(
                "AlphaFold returned an unexpected content type for the structure.",
                details={"content_type": content_type},
            )
        _validate_structure_payload(payload, suffix)
        checksum = hashlib.sha256(payload).hexdigest()
        retrieved_at = utc_now_iso()
        chain = str(entry.get("chainId") or "A")
        structure_info = StructureInfo(
            accession=accession,
            source="AlphaFold DB",
            model_version=_version_label(entry),
            chain=chain,
            url=url,
            checksum_sha256=checksum,
            retrieved_at=retrieved_at,
            is_predicted=True,
            confidence_source="plddt",
            file_format=suffix.lstrip("."),
            file_size_bytes=len(payload),
            tool_used=str(entry.get("toolUsed") or "AlphaFold"),
            model_created_date=str(entry.get("modelCreatedDate") or ""),
            mode="live",
        )
        return AlphaFoldArtifact(
            payload=payload,
            structure_info=structure_info,
            suffix=suffix,
            metadata=entry,
        )
