from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, status

from aegisops.core.config import get_settings


def verify_webhook_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = get_settings().alertmanager_webhook_token.get_secret_value()

    if not expected or not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized webhook request",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized webhook request",
        )
