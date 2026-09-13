from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SyncRun
from app.models.enums import SyncStatus


class SyncRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self) -> SyncRun:
        run = SyncRun(status=SyncStatus.RUNNING)
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: int) -> SyncRun:
        run = self.session.get(SyncRun, run_id)
        if run is None:
            raise RuntimeError("Sync run disappeared")
        return run

    def list(self, offset: int, limit: int) -> list[SyncRun]:
        return list(
            self.session.scalars(
                select(SyncRun).order_by(SyncRun.id.desc()).offset(offset).limit(limit),
            )
        )
