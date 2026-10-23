from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from aegisops.core.auth import (
    AuthenticatedActor,
    _load_configured_actors,
    get_current_actor,
)
from aegisops.core.config import get_settings
from aegisops.core.csrf import generate_csrf_token
from aegisops.core.rate_limit import rate_limit_auth

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])


class CurrentActorResponse(BaseModel):
    identity: str
    roles: list[str]
    can_approve: bool
    can_request: bool
    can_execute: bool
    can_verify: bool
    can_assess_rollback: bool
    csrf_token: str | None = None
    dev_persona_switching_enabled: bool = False


class SessionLoginRequest(BaseModel):
    token: str | None = None
    identity: str | None = None


class ActorProfile(BaseModel):
    identity: str
    roles: list[str]


@router.get("/me", response_model=CurrentActorResponse)
async def get_current_user_profile(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
):
    settings = get_settings()
    csrf_token = (
        generate_csrf_token(actor.session_token) if actor.session_token else None
    )
    return CurrentActorResponse(
        identity=actor.identity,
        roles=sorted(actor.roles),
        can_approve=actor.can_approve,
        can_request=actor.can_request,
        can_execute=actor.can_execute,
        can_verify=actor.can_verify,
        can_assess_rollback=actor.can_assess_rollback,
        csrf_token=csrf_token,
        dev_persona_switching_enabled=settings.dev_persona_switching_allowed,
    )


@router.get("/csrf")
async def get_csrf_token(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
):
    """Returns a session-bound CSRF token for the authenticated cookie session."""
    if actor.session_token:
        token = generate_csrf_token(actor.session_token)
        return {"csrf_token": token}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="CSRF token is only applicable to cookie-based sessions",
    )


@router.get("/actors", response_model=list[ActorProfile])
@router.get("/personas", response_model=list[ActorProfile])
async def list_available_dev_actors():
    """Returns non-sensitive configured actor profiles for local development UI testing."""
    settings = get_settings()
    if not settings.dev_persona_switching_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor listing is restricted to development environments with persona switching enabled",
        )

    actors = _load_configured_actors()
    profiles: list[ActorProfile] = []
    seen = set()
    for info in actors.values():
        ident = str(info.get("identity", "unknown"))
        if ident in seen:
            continue
        seen.add(ident)
        raw_roles = info.get("roles", [])
        role_list = raw_roles if isinstance(raw_roles, list) else [str(raw_roles)]
        profiles.append(ActorProfile(identity=ident, roles=sorted(role_list)))
    return profiles


@router.post(
    "/session",
    response_model=CurrentActorResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def create_session(
    payload: SessionLoginRequest,
    response: Response,
):
    """Establishes an authenticated session using secure HttpOnly and CSRF cookies."""
    settings = get_settings()
    configured_actors = _load_configured_actors()
    matched_token: str | None = None
    matched_actor: dict | None = None

    if payload.token:
        for cfg_token, actor_info in configured_actors.items():
            if compare_digest(payload.token.strip(), cfg_token):
                matched_token = cfg_token
                matched_actor = actor_info
                break
    elif payload.identity:
        if not settings.dev_persona_switching_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Development persona switching is disabled in this environment",
            )
        for cfg_token, actor_info in configured_actors.items():
            if actor_info.get("identity") == payload.identity:
                matched_token = cfg_token
                matched_actor = actor_info
                break

    if not matched_token or not matched_actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials or unrecognized identity",
        )

    csrf_token = generate_csrf_token(matched_token)
    cookie_secure = settings.session_cookie_secure or settings.is_production

    # Set secure HttpOnly session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=matched_token,
        httponly=True,
        samesite="lax",
        secure=cookie_secure,
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    # Set companion CSRF token cookie readable by client application
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=cookie_secure,
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    identity = str(matched_actor.get("identity", "unknown"))
    raw_roles = matched_actor.get("roles", [])
    roles = (
        frozenset(raw_roles)
        if isinstance(raw_roles, list)
        else frozenset([str(raw_roles)])
    )
    actor = AuthenticatedActor(
        identity=identity,
        roles=roles,
        auth_method="cookie",
        session_token=matched_token,
    )

    return CurrentActorResponse(
        identity=actor.identity,
        roles=sorted(actor.roles),
        can_approve=actor.can_approve,
        can_request=actor.can_request,
        can_execute=actor.can_execute,
        can_verify=actor.can_verify,
        can_assess_rollback=actor.can_assess_rollback,
        csrf_token=csrf_token,
        dev_persona_switching_enabled=settings.dev_persona_switching_allowed,
    )


@router.post("/logout")
async def logout(
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
):
    """Clears both the session cookie and CSRF token."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        httponly=False,
        samesite="lax",
    )
    return {"status": "logged_out", "message": "Logged out successfully"}
