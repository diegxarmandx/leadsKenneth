"""Idempotent configuration seed. Apply Alembic migrations first; never creates leads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.db.session import make_engine, make_session_factory, write_session  # noqa: E402
from app.repositories.pricing_rule_repository import PricingRuleRepository  # noqa: E402
from app.repositories.settings_repository import SettingsRepository  # noqa: E402
from app.services.pricing_service import PricingService  # noqa: E402
from app.services.settings_service import SettingsService  # noqa: E402

DEFAULT_RULES = [(0, 7, 3000, 30), (8, 30, 2000, 20), (31, 60, 1200, 10), (61, None, 500, 5)]


def seed(session, config: Settings) -> None:
    repository = PricingRuleRepository(session)
    if not repository.list():
        for order, (minimum, maximum, price, exclusion) in enumerate(DEFAULT_RULES):
            repository.add(
                {
                    "min_age_days": minimum,
                    "max_age_days": maximum,
                    "price_cents": price,
                    "exclusion_days": exclusion,
                    "sort_order": order,
                    "is_active": True,
                }
            )
        session.flush()
    PricingService.validate_ranges(repository.list())
    settings = SettingsRepository(session)
    existing = settings.all()
    for key, value in SettingsService(session, config).defaults.items():
        if key not in existing and value:
            settings.set(key, value)


if __name__ == "__main__":
    config = Settings()
    engine = make_engine(config.database_url)
    with write_session(make_session_factory(engine)) as session:
        seed(session, config)
    engine.dispose()
    print("Default pricing and non-secret settings initialized. No leads created.")
