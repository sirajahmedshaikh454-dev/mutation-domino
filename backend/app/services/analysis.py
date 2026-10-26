from __future__ import annotations

from app.core.config import Settings
from app.core.time import utc_now_iso
from app.domain.analysis import run_analysis, validate_parameters
from app.domain.errors import AnalysisFailed
from app.domain.models import AnalysisParameters
from app.persistence.repositories import AnalysisRecord, AnalysisRepository
from app.services.proteins import ProteinService


class AnalysisService:
    def __init__(
        self,
        settings: Settings,
        proteins: ProteinService,
        repository: AnalysisRepository,
    ) -> None:
        self.settings = settings
        self.proteins = proteins
        self.repository = repository

    async def create(
        self,
        *,
        accession: str,
        variant: str,
        parameters: AnalysisParameters | None = None,
    ) -> AnalysisRecord:
        params = parameters or validate_parameters()
        bundle = await self.proteins.load(accession)
        try:
            result = run_analysis(
                protein=bundle.protein,
                structure=bundle.structure,
                structure_info=bundle.structure_info,
                variant_text=variant,
                parameters=params,
                schema_version=self.settings.schema_version,
                algorithm_version=self.settings.algorithm_version,
                generated_at=utc_now_iso(),
                max_contact_rows=self.settings.max_contact_rows,
            )
        except Exception as exc:
            if hasattr(exc, "code"):
                raise
            raise AnalysisFailed(
                "The structural-context analysis could not be completed.",
                details={"reason": type(exc).__name__},
            ) from exc
        return self.repository.create(
            protein=bundle.protein,
            structure_info=bundle.structure_info,
            structure_path=str(bundle.structure_path),
            mapping=result["mapping"],
            variant=result["variant"]["normalized"],
            parameters=params.to_dict(),
            result=result,
            algorithm_version=self.settings.algorithm_version,
            schema_version=self.settings.schema_version,
            warnings=result["warnings"],
        )

    def get(self, analysis_id: str) -> AnalysisRecord:
        return self.repository.get(analysis_id)

    def list(self, *, limit: int = 20, offset: int = 0) -> tuple[list[AnalysisRecord], int]:
        return self.repository.list(limit=limit, offset=offset)
