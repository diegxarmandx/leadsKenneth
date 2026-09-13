from datetime import datetime

from sqlalchemy import Enum, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.models.enums import SyncStatus
from app.utils.time import utcnow


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False, create_constraint=True, name="sync_status"),
    )
    rows_received: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    leads_created: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    leads_updated: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    leads_deactivated: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    leads_reactivated: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    error_message: Mapped[str | None] = mapped_column(Text)
