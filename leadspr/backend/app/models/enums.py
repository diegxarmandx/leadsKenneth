from enum import StrEnum


class PurchaseStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FULFILLED = "FULFILLED"
    FAILED = "FAILED"
    FULFILLMENT_FAILED = "FULFILLMENT_FAILED"


class SyncStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ActorType(StrEnum):
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"
