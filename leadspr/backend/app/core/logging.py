import json
import logging

from app.utils.time import utcnow


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Never serialize exception text, HTTP bodies, tokens, or lead/buyer fields.
        data = {
            "timestamp": utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("public_id", "sync_run_id", "error_type", "request_id"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger("app").handlers = [handler]
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("app").propagate = False
    for name in ("httpx", "httpcore", "stripe", "googleapiclient"):
        logging.getLogger(name).setLevel(logging.WARNING)
