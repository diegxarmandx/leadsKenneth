from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def all(self) -> dict[str, str]:
        return {item.key: item.value for item in self.session.scalars(select(AppSetting))}

    def set(self, key: str, value: str) -> None:
        row = self.session.scalar(select(AppSetting).where(AppSetting.key == key))
        if row is None:
            self.session.add(AppSetting(key=key, value=value))
        else:
            row.value = value
