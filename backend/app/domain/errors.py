from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Transport-agnostic error with a stable machine-readable code."""

    code = "DOMAIN_ERROR"
    http_status = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class InvalidAccession(DomainError):
    code = "INVALID_ACCESSION"
    http_status = 422


class ProteinNotFound(DomainError):
    code = "PROTEIN_NOT_FOUND"
    http_status = 404


class StructureUnavailable(DomainError):
    code = "STRUCTURE_UNAVAILABLE"
    http_status = 404


class InvalidVariant(DomainError):
    code = "INVALID_VARIANT"
    http_status = 422


class VariantWtMismatch(DomainError):
    code = "VARIANT_WT_MISMATCH"
    http_status = 422


class PositionUnmapped(DomainError):
    code = "POSITION_UNMAPPED"
    http_status = 422


class AmbiguousMapping(DomainError):
    code = "AMBIGUOUS_MAPPING"
    http_status = 422


class InvalidParameters(DomainError):
    code = "INVALID_PARAMETERS"
    http_status = 422


class StructureTooLarge(DomainError):
    code = "STRUCTURE_TOO_LARGE"
    http_status = 413


class MalformedStructure(DomainError):
    code = "MALFORMED_STRUCTURE"
    http_status = 502


class AnalysisFailed(DomainError):
    code = "ANALYSIS_FAILED"
    http_status = 500


class UpstreamTimeout(DomainError):
    code = "UPSTREAM_TIMEOUT"
    http_status = 504


class UpstreamError(DomainError):
    code = "UPSTREAM_ERROR"
    http_status = 502


class RateLimited(DomainError):
    code = "UPSTREAM_RATE_LIMITED"
    http_status = 503


class NotFound(DomainError):
    code = "ANALYSIS_NOT_FOUND"
    http_status = 404
