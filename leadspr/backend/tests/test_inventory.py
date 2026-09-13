from datetime import timedelta

import pytest

from app.services.inventory_service import InventoryService
from tests.conftest import exclusion


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_active": False},
        {"municipality": "Ponce"},
        {"insurance_type": "Other"},
        {"age": 3},
        {"age": -1},
    ],
)
def test_ineligible_leads_are_excluded(env, add_lead, overrides):
    add_lead(**overrides)
    with env.factory() as session:
        service = InventoryService(session, env.config, env.now)
        assert service.count(price_cents=2000, municipality="Bayamón") == 0


@pytest.mark.parametrize("delta,expected", [(1, 0), (0, 1), (-1, 1)])
def test_exclusion_expiration_boundary(env, add_lead, delta, expected):
    lead_id = add_lead()
    exclusion(env, lead_id, env.now + timedelta(seconds=delta))
    with env.factory() as session:
        assert InventoryService(session, env.config, env.now).count(price_cents=2000) == expected


def test_summary_and_municipalities_are_eligible_aggregates(env, add_lead):
    add_lead(age=0)
    add_lead()
    add_lead(municipality="Ponce", source_active=False)
    add_lead(municipality="San Juan", age=-1)
    with env.factory() as session:
        service = InventoryService(session, env.config, env.now)
        assert service.municipalities() == ["Bayamón"]
        assert {
            tier["price_cents"]: tier["available_quantity"] for tier in service.summary()["tiers"]
        } == {
            3000: 1,
            2000: 1,
            1200: 0,
            500: 0,
        }
