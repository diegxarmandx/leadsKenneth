class DomainError(Exception):
    status_code = 400
    code = "invalid_input"


class ConfigurationError(DomainError):
    status_code = 503
    code = "integration_not_configured"


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class InsufficientInventoryError(DomainError):
    status_code = 409
    code = "insufficient_inventory"


class PricingRuleNotFoundError(DomainError):
    code = "pricing_rule_not_found"


class PricingRuleConflictError(DomainError):
    status_code = 409
    code = "pricing_rule_conflict"


class PurchaseAlreadyFulfilledError(DomainError):
    status_code = 409
    code = "purchase_already_fulfilled"


class SheetSyncError(DomainError):
    status_code = 502
    code = "sheet_sync_failed"


class FulfillmentError(DomainError):
    status_code = 409
    code = "fulfillment_failed"


class IntegrationError(DomainError):
    status_code = 502
    code = "integration_failed"


class EmailDeliveryError(IntegrationError):
    code = "email_delivery_pending"


class EmailDeliveryBlocked(IntegrationError):
    """Delivery needs a recipient/configuration correction, not another retry."""

    code = "email_delivery_blocked"

    def __init__(self, *, provider_status: int | None = None, reason: str = "requires_review"):
        super().__init__(
            "El envío del correo requiere revisión administrativa. "
            "Los leads siguen asignados; no necesitas volver a pagar."
        )
        self.provider_status, self.reason = provider_status, reason
