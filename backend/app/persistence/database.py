from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.persistence.tables import Base

_ENGINES: dict[str, Engine] = {}


def get_engine(database_url: str) -> Engine:
    if database_url not in _ENGINES:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
            db_path = Path(database_url.removeprefix("sqlite:///"))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url, connect_args=connect_args, future=True)
        _ENGINES[database_url] = engine
    return _ENGINES[database_url]


def init_db(settings: Settings) -> Engine:
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(engine)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
