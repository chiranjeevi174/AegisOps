import json
from dataclasses import dataclass
from hmac import compare_digest
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from aegisops.core.config import get_settings
from aegisops.core.csrf import is_allowed_origin, validate_csrf_token


@dataclass(frozen=True)
class AuthenticatedActor:
    identity: str
    roles: frozenset[str]
    auth_method: str = "bearer"
    session_token: str | None = None

    @property
    def can_approve(self) -> bool:
        return "approver" in self.roles or "admin" in self.roles

    @property
    def can_request(self) -> bool:
        return "requester" in self.roles or "admin" in self.roles

    @property
    def can_execute(self) -> bool:
        return (
            "operator" in self.roles
            or "executor" in self.roles
            or "admin" in self.roles
        )

    @property
    def can_verify(self) -> bool:
        return (
            "verifier" in self.roles
            or "operator" in self.roles
            or "executor" in self.roles
            or "admin" in self.roles
        )

    @property
    def can_assess_rollback(self) -> bool:
        return (
            "rollback_assessor" in self.roles
            or "operator" in self.roles
            or "executor" in self.roles
            or "verifier" in self.roles
            or "admin" in self.roles
        )

    @property
    def can_analyze(self) -> bool:
        return (
            "operator" in self.roles
            or "executor" in self.roles
            or "requester" in self.roles
            or "approver" in self.roles
            or "admin" in self.roles
        )


def _load_configured_actors() -> dict[str, dict[str, str | list[str]]]:
    raw = get_settings().human_auth_tokens.get_secret_value().strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    actors: dict[str, dict[str, str | list[str]]] = {}
    for entry in raw.split(","):
        parts = entry.strip().split(":")
        if len(parts) >= 3:
            token, identity, roles_str = parts[0], parts[1], parts[2]
            actors[token] = {
                "identity": identity,
                "roles": [r.strip() for r in roles_str.split("+")],
            }
    return actors


def get_current_actor(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Cookie(alias="aegisops_session")] = None,
    x_csrf_token: Annotated[str | None, Header(alias="x-csrf-token")] = None,
) -> AuthenticatedActor:
    token: str | None = None
    auth_method = "bearer"

    if authorization:
        scheme, _, bearer_token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not bearer_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme; Bearer token required",
            )
        token = bearer_token
        auth_method = "bearer"
    elif session_token:
        token = session_token
        auth_method = "cookie"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or session cookie",
        )

    configured_actors = _load_configured_actors()

    # Constant-time token lookup
    matched_actor: dict[str, str | list[str]] | None = None
    for configured_token, actor_info in configured_actors.items():
        if compare_digest(token, configured_token):
            matched_actor = actor_info
            break

    if not matched_actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unrecognized authentication token",
        )

    # Mandatory CSRF validation for cookie-authenticated state-changing requests
    if auth_method == "cookie" and request.method.upper() in {
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
    }:
        origin = request.headers.get("origin")
        if origin and not is_allowed_origin(origin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Untrusted cross-origin request rejected",
            )

        referer = request.headers.get("referer")
        if referer and not origin and not is_allowed_origin(referer):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Untrusted referer header rejected",
            )

        if not validate_csrf_token(token, x_csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Invalid or missing CSRF token for cookie-authenticated session",
            )

    identity = str(matched_actor.get("identity", "unknown"))
    raw_roles = matched_actor.get("roles", [])
    roles = (
        frozenset(raw_roles)
        if isinstance(raw_roles, list)
        else frozenset([str(raw_roles)])
    )

    return AuthenticatedActor(
        identity=identity,
        roles=roles,
        auth_method=auth_method,
        session_token=token if auth_method == "cookie" else None,
    )


def get_approver_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_approve:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks approval permission",
        )
    return actor


def get_requester_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_request:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks approval request creation permission",
        )
    return actor


def get_executor_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_execute:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks execution permission",
        )
    return actor


def get_verifier_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_verify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks verification permission",
        )
    return actor


def get_rollback_assessor_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_assess_rollback:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks rollback assessment permission",
        )
    return actor


def get_incident_analyzer_actor(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
) -> AuthenticatedActor:
    if not actor.can_analyze:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: actor '{actor.identity}' lacks incident analysis permission",
        )
    return actor
