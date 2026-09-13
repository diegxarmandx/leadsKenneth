from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.runtime import Runtime
from app.db.session import write_session


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]


def get_session(runtime: RuntimeDep) -> Iterator[Session]:
    with runtime.sessions() as session:
        yield session


def get_write_session(runtime: RuntimeDep) -> Iterator[Session]:
    with write_session(runtime.sessions) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
WriteSessionDep = Annotated[Session, Depends(get_write_session, scope="function")]
