from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str) -> Engine:
    sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30} if sqlite else {},
        pool_pre_ping=True,
    )
    if sqlite:

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _record):
            # Explicit BEGIN avoids sqlite3 legacy transaction control for SELECT/DDL.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        @event.listens_for(engine, "begin")
        def begin(connection):
            mode = connection.get_execution_options().get("sqlite_begin_mode", "DEFERRED")
            connection.exec_driver_sql(f"BEGIN {mode}")

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def write_session(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Acquire SQLite's write lock BEFORE eligibility reads, across processes."""
    with factory() as session:
        try:
            if session.get_bind().dialect.name == "sqlite":
                session.connection(execution_options={"sqlite_begin_mode": "IMMEDIATE"})
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


def lock_path(engine: Engine, purpose: str) -> str:
    database = engine.url.database or "leadspr"
    return str(Path(database).resolve()) + f".{purpose}.lock"
