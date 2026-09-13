from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.exceptions import PricingRuleConflictError
from app.db.session import write_session
from app.models import Lead
from app.schemas.pricing import PricingRuleInput, PricingRulePatch, PricingRuleUpdate
from app.services.pricing_service import PricingService
from app.utils.time import business_date


@pytest.mark.parametrize(
    "age,price",
    [(0, 3000), (7, 3000), (8, 2000), (30, 2000), (31, 1200), (60, 1200), (61, 500), (10000, 500)],
)
def test_price_boundaries(env, age, price):
    with env.factory() as session:
        service = PricingService(session)
        rule = service.applicable_rule(env.today - timedelta(days=age), env.today, service.list())
        assert rule.price_cents == price


def test_price_changes_by_calendar_day_without_lead_mutation(env, add_lead):
    lead_id = add_lead(age=7)
    with env.factory() as session:
        lead = session.get(Lead, lead_id)
        service = PricingService(session)
        assert (
            service.applicable_rule(lead.lead_date, env.today, service.list()).price_cents == 3000
        )
        assert (
            service.applicable_rule(
                lead.lead_date, env.today + timedelta(days=1), service.list()
            ).price_cents
            == 2000
        )
        assert not session.dirty
        assert (
            service.applicable_rule(env.today + timedelta(days=1), env.today, service.list())
            is None
        )


def test_puerto_rico_calendar_boundary():
    assert business_date("America/Puerto_Rico", datetime(2026, 9, 12, 3, 59, tzinfo=UTC)) == date(
        2026, 9, 11
    )
    assert business_date("America/Puerto_Rico", datetime(2026, 9, 12, 4, 0, tzinfo=UTC)) == date(
        2026, 9, 12
    )


@pytest.mark.parametrize("patch", [{"min_age_days": 7}, {"min_age_days": 9}, {"is_active": False}])
def test_overlap_gap_and_deactivation_rejected_atomically(env, patch):
    with pytest.raises(PricingRuleConflictError), write_session(env.factory) as session:
        PricingService(session).update(2, PricingRulePatch(**patch))
    with env.factory() as session:
        rule = PricingService(session).repository.get(2)
        assert rule.min_age_days == 8 and rule.is_active


@pytest.mark.parametrize(
    "values",
    [
        {"min_age_days": -1},
        {"max_age_days": -1},
        {"price_cents": 0},
        {"exclusion_days": -1},
        {"min_age_days": 3, "max_age_days": 2},
    ],
)
def test_invalid_rule_values(values):
    with pytest.raises(ValidationError):
        PricingRuleInput(**({"min_age_days": 0, "price_cents": 500, "exclusion_days": 0} | values))


def test_adjacent_ranges_can_be_changed_atomically(env):
    with write_session(env.factory) as session:
        service = PricingService(session)
        items = [
            PricingRuleUpdate.model_validate(rule, from_attributes=True) for rule in service.list()
        ]
        items[0].max_age_days = 10
        items[1].min_age_days = 11
        result = service.update_batch(items)
        assert result[0].max_age_days == 10 and result[1].min_age_days == 11
