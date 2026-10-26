from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from app.core.time import utc_now_iso
from app.domain.errors import ProteinNotFound, UpstreamError
from app.domain.models import ProteinInfo
from app.integrations.http import BoundedHttpClient, UpstreamStatusError


def _first_name(protein_description: dict[str, Any]) -> str:
    recommended = protein_description.get("recommendedName") or {}
    full_name = (recommended.get("fullName") or {}).get("value")
    if full_name:
        return str(full_name)
    for submission in protein_description.get("submissionNames") or []:
        value = (submission.get("fullName") or {}).get("value")
        if value:
            return str(value)
    for alternative in protein_description.get("alternativeNames") or []:
        value = (alternative.get("fullName") or {}).get("value")
        if value:
            return str(value)
    return "Unnamed protein"


def _gene_name(genes: list[dict[str, Any]]) -> str | None:
    for gene in genes:
        value = (gene.get("geneName") or {}).get("value")
        if value:
            return str(value)
    return None


def protein_info_from_payload(
    payload: object,
    *,
    source_url: str,
    retrieved_at: str | None = None,
    mode: str = "live",
) -> ProteinInfo:
    if not isinstance(payload, dict):
        raise UpstreamError("UniProt returned an unexpected payload shape.")
    accession = str(payload.get("primaryAccession") or "").strip().upper()
    sequence_block = payload.get("sequence") or {}
    sequence = str(sequence_block.get("value") or "").strip().upper()
    length = sequence_block.get("length")
    if not accession or not sequence:
        raise UpstreamError("UniProt returned no canonical sequence for this entry.")
    if not isinstance(length, int) or length != len(sequence):
        raise UpstreamError("UniProt sequence length is inconsistent with the returned sequence.")
    organism = (payload.get("organism") or {}).get("scientificName") or "Unknown organism"
    entry_audit = payload.get("entryAudit") or {}
    entry_version = entry_audit.get("entryVersion")
    sequence_version = sequence_block.get("version") or entry_audit.get("sequenceVersion")
    version_parts = []
    if entry_version is not None:
        version_parts.append(f"entry v{entry_version}")
    if sequence_version is not None:
        version_parts.append(f"sequence v{sequence_version}")
    return ProteinInfo(
        accession=accession,
        name=_first_name(payload.get("proteinDescription") or {}),
        organism=str(organism),
        sequence=sequence,
        length=len(sequence),
        gene=_gene_name(payload.get("genes") or []),
        source_url=source_url,
        retrieved_at=retrieved_at or utc_now_iso(),
        source_version=", ".join(version_parts) or str(payload.get("entryType") or "UniProtKB"),
        mode=mode,
        metadata={
            "entry_type": payload.get("entryType"),
            "annotation_score": payload.get("annotationScore"),
            "reviewed": "reviewed" in str(payload.get("entryType", "")).lower(),
        },
    )


class UniProtAdapter:
    def __init__(self, client: BoundedHttpClient, base_url: str, *, max_length: int) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._max_length = max_length
        host = urlsplit(self._base_url).hostname
        self._allowed_hosts = (host,) if host else ()

    def _url(self, accession: str) -> str:
        return f"{self._base_url}/uniprotkb/{accession}.json"

    async def fetch_payload(self, accession: str) -> tuple[object, str]:
        url = self._url(accession)
        try:
            payload = await self._client.get_json(url, allowed_hosts=self._allowed_hosts)
        except UpstreamStatusError as exc:
            if exc.status_code == 404:
                raise ProteinNotFound(
                    f"UniProt has no entry for accession {accession}.",
                    details={"accession": accession},
                ) from exc
            if exc.status_code == 400:
                raise ProteinNotFound(
                    f"UniProt rejected accession {accession}.",
                    details={"accession": accession},
                ) from exc
            raise
        return payload, url

    async def fetch(self, accession: str) -> ProteinInfo:
        payload, url = await self.fetch_payload(accession)
        protein = protein_info_from_payload(payload, source_url=url)
        if protein.accession != accession:
            raise UpstreamError(
                "UniProt returned a different primary accession than requested.",
                details={"requested": accession, "returned": protein.accession},
            )
        if protein.length > self._max_length:
            raise UpstreamError(
                "The protein exceeds the configured length limit.",
                details={"length": protein.length, "limit": self._max_length},
            )
        return protein
