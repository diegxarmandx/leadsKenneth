import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies.runtime import RuntimeDep
from app.core.exceptions import ConfigurationError

bearer = HTTPBearer(auto_error=False)


def require_admin(
    runtime: RuntimeDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    token = runtime.config.admin_api_token.get_secret_value()
    if len(token) < 32:
        raise ConfigurationError("Configure ADMIN_API_TOKEN with at least 32 random characters")
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(),
        token.encode(),
    ):
        raise HTTPException(
            401, "Admin authentication required", headers={"WWW-Authenticate": "Bearer"}
        )
