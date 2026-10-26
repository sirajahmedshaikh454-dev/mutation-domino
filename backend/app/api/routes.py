from __future__ import annotations

import re

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, Response

from app.api.schemas import (
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSummary,
    HealthResponse,
    ProteinResponse,
    StructureSummary,
)
from app.core.time import utc_now_iso
from app.domain.analysis import validate_parameters
from app.exports.json_export import build_json_export
from app.exports.pdf_export import build_pdf_report
from app.persistence.repositories import AnalysisRecord
from app.services.analysis import AnalysisService
from app.services.proteins import ProteinBundle, ProteinService

router = APIRouter()
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")


def _analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def _protein_service(request: Request) -> ProteinService:
    return request.app.state.protein_service


def _protein_response(bundle: ProteinBundle, request: Request) -> ProteinResponse:
    info = bundle.structure_info
    settings = request.app.state.settings
    return ProteinResponse(
        accession=bundle.protein.accession,
        name=bundle.protein.name,
        organism=bundle.protein.organism,
        gene=bundle.protein.gene,
        length=bundle.protein.length,
        sequence=bundle.protein.sequence,
        provenance={
            "source": "UniProt REST",
            "source_url": bundle.protein.source_url,
            "retrieved_at": bundle.protein.retrieved_at,
            "source_version": bundle.protein.source_version,
            "mode": bundle.protein.mode,
        },
        structure=StructureSummary(
            source=info.source,
            is_predicted=info.is_predicted,
            confidence_source=info.confidence_source,
            model_version=info.model_version,
            chain=info.chain,
            url=info.url,
            checksum_sha256=info.checksum_sha256,
            retrieved_at=info.retrieved_at,
            file_format=info.file_format,
            file_size_bytes=info.file_size_bytes,
            tool_used=info.tool_used,
            model_created_date=info.model_created_date,
            mode=info.mode,
            coverage={
                "structure_residues": len(bundle.structure.residues),
                "canonical_length": bundle.protein.length,
                "observed_sequence_length": len(bundle.structure.sequence),
            },
            download_path=f"{settings.api_prefix}/proteins/{bundle.protein.accession}/structure",
        ),
        warnings=list(bundle.structure.warnings),
    )


def _analysis_response(record: AnalysisRecord) -> AnalysisResponse:
    return AnalysisResponse(**record.envelope())


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def api_health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        mode=settings.mode,
        schema_version=settings.schema_version,
        time=utc_now_iso(),
    )


@router.get("/proteins/{accession}", response_model=ProteinResponse, tags=["proteins"])
async def get_protein(accession: str, request: Request) -> ProteinResponse:
    bundle = await _protein_service(request).load(accession)
    return _protein_response(bundle, request)


@router.get("/proteins/{accession}/structure", tags=["proteins"])
async def get_protein_structure(accession: str, request: Request) -> FileResponse:
    bundle = await _protein_service(request).load(accession)
    media_type = "chemical/x-mmcif" if bundle.structure_info.file_format == "cif" else "chemical/x-pdb"
    safe_accession = SAFE_FILENAME.sub("_", bundle.protein.accession)
    safe_version = SAFE_FILENAME.sub("_", bundle.structure_info.model_version)
    extension = "cif" if bundle.structure_info.file_format == "cif" else "pdb"
    filename = f"{safe_accession}_{safe_version}.{extension}"
    return FileResponse(
        path=bundle.structure_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/analyses", response_model=AnalysisResponse, status_code=201, tags=["analyses"])
async def create_analysis(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
    parameters = validate_parameters(
        payload.parameters.ca_radius_angstrom,
        payload.parameters.heavy_atom_radius_angstrom,
    )
    record = await _analysis_service(request).create(
        accession=payload.accession,
        variant=payload.variant,
        parameters=parameters,
    )
    return _analysis_response(record)


@router.get("/analyses", response_model=AnalysisListResponse, tags=["analyses"])
async def list_analyses(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
) -> AnalysisListResponse:
    records, total = _analysis_service(request).list(limit=limit, offset=offset)
    return AnalysisListResponse(
        items=[AnalysisSummary(**record.summary()) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse, tags=["analyses"])
async def get_analysis(analysis_id: str, request: Request) -> AnalysisResponse:
    return _analysis_response(_analysis_service(request).get(analysis_id))


@router.get("/analyses/{analysis_id}/export.json", tags=["exports"])
async def export_analysis_json(analysis_id: str, request: Request) -> Response:
    record = _analysis_service(request).get(analysis_id)
    payload = build_json_export(record)
    filename = f"mutation-domino-{SAFE_FILENAME.sub('_', record.id)}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/analyses/{analysis_id}/report.pdf", tags=["exports"])
async def export_analysis_pdf(analysis_id: str, request: Request) -> Response:
    record = _analysis_service(request).get(analysis_id)
    payload = build_pdf_report(record)
    filename = f"mutation-domino-{SAFE_FILENAME.sub('_', record.id)}.pdf"
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
