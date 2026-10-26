from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import install_error_handlers
from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.time import utc_now_iso
from app.persistence.database import init_db, make_session_factory
from app.persistence.repositories import AnalysisRepository
from app.services.analysis import AnalysisService
from app.services.proteins import ProteinService

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = init_db(app_settings)
        session_factory = make_session_factory(engine)
        repository = AnalysisRepository(session_factory)
        protein_service = ProteinService(app_settings)
        app.state.settings = app_settings
        app.state.engine = engine
        app.state.repository = repository
        app.state.protein_service = protein_service
        app.state.analysis_service = AnalysisService(app_settings, protein_service, repository)
        logger.info(
            "Mutation Domino started (mode=%s, db=%s, cache=%s)",
            app_settings.mode,
            app_settings.database_url,
            app_settings.cache_dir,
        )
        yield
        engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Wild-type structural-context explorer for missense variants. "
            "Research and education only; not a clinical or pathogenicity predictor."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )
    install_error_handlers(app)
    app.include_router(router, prefix=app_settings.api_prefix)

    @app.get("/health", tags=["system"])
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "app": app_settings.app_name,
                "version": app_settings.app_version,
                "mode": app_settings.mode,
                "schema_version": app_settings.schema_version,
                "time": utc_now_iso(),
            }
        )

    @app.get("/", include_in_schema=False)
    async def index() -> JSONResponse:
        return JSONResponse(
            {
                "app": app_settings.app_name,
                "version": app_settings.app_version,
                "api": app_settings.api_prefix,
                "docs": "/docs",
                "health": "/health",
                "disclaimer": "Research and education only. Not for clinical decision-making.",
            }
        )

    return app


app = create_app()
