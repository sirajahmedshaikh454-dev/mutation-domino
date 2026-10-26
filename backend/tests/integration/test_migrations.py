from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

BACKEND = Path(__file__).resolve().parents[2]


def alembic_config(db_path: Path) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    return config


def test_upgrade_and_downgrade_on_empty_database(tmp_path) -> None:
    db_path = tmp_path / "migration.db"
    config = alembic_config(db_path)
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {"proteins", "structures", "analyses", "alembic_version"} <= tables
    indexes = {index["name"] for index in inspect(engine).get_indexes("analyses")}
    assert "ix_analyses_accession" in indexes
    assert "ix_analyses_created_at" in indexes
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    remaining = set(inspect(engine).get_table_names())
    assert not {"proteins", "structures", "analyses"} & remaining
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    assert "analyses" in inspect(engine).get_table_names()
    engine.dispose()
