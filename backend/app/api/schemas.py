from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ParametersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ca_radius_angstrom: float = Field(default=8.0, ge=4.0, le=20.0)
    heavy_atom_radius_angstrom: float = Field(default=5.0, ge=2.0, le=10.0)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "accession": "P69905",
                "variant": "N10V",
                "parameters": {"ca_radius_angstrom": 8.0, "heavy_atom_radius_angstrom": 5.0},
            }
        },
    )

    accession: str = Field(min_length=1, max_length=20)
    variant: str = Field(min_length=1, max_length=20)
    parameters: ParametersRequest = Field(default_factory=ParametersRequest)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    version: str
    mode: str
    schema_version: str
    time: str


class StructureSummary(BaseModel):
    available: bool = True
    source: str
    is_predicted: bool
    confidence_source: str
    model_version: str
    chain: str
    url: str
    checksum_sha256: str
    retrieved_at: str
    file_format: str
    file_size_bytes: int
    tool_used: str = ""
    model_created_date: str = ""
    mode: str
    coverage: dict[str, Any] = Field(default_factory=dict)
    download_path: str = ""


class ProteinResponse(BaseModel):
    accession: str
    name: str
    organism: str
    gene: str | None = None
    length: int
    sequence: str
    provenance: dict[str, Any]
    structure: StructureSummary
    warnings: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    id: str
    status: str
    created_at: str
    result: dict[str, Any]


class AnalysisSummary(BaseModel):
    id: str
    accession: str
    variant: str
    protein_name: str
    organism: str
    status: str
    created_at: str
    structure_source: str = ""
    model_version: str = ""


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]
    total: int
    limit: int
    offset: int
