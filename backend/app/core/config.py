from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime configuration. All values can be overridden by environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MUTATION_DOMINO_",
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mutation Domino"
    app_version: str = "0.1.0"
    schema_version: str = "1.0.0"
    algorithm_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    mode: Literal["live", "fixture"] = "live"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'mutation_domino.db').as_posix()}"
    cache_dir: Path = BACKEND_DIR / "data" / "cache"
    max_cache_bytes: int = 200 * 1024 * 1024
    cache_ttl_seconds: int = 24 * 60 * 60

    uniprot_base_url: str = "https://rest.uniprot.org"
    alphafold_base_url: str = "https://alphafold.ebi.ac.uk"
    user_agent: str = "MutationDomino/0.1 (research/education; local deployment)"
    connect_timeout_seconds: float = 8.0
    read_timeout_seconds: float = 45.0
    max_metadata_bytes: int = 4 * 1024 * 1024
    max_structure_bytes: int = 30 * 1024 * 1024
    max_protein_length: int = 4000
    max_structure_residues: int = 5000

    frontend_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )

    ca_radius_min: float = 4.0
    ca_radius_max: float = 20.0
    heavy_atom_radius_min: float = 2.0
    heavy_atom_radius_max: float = 10.0
    max_contact_rows: int = 500
    max_neighbor_rows: int = 500

    offline_fixture_dir: Path = BACKEND_DIR / "tests" / "fixtures"

    @property
    def allowed_structure_hosts(self) -> tuple[str, ...]:
        return ("alphafold.ebi.ac.uk",)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
