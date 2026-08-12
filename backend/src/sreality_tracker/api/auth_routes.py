"""Google OAuth entry points and owner session lifecycle."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from sreality_tracker.api.auth import (
    OAUTH_FLOW_COOKIE,
    OAUTH_FLOW_MAX_AGE_SECONDS,
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    AuthManager,
    AuthTokenError,
)
from sreality_tracker.api.contracts import ApiModel
from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.owner import AuthenticatedOwner

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthSessionResponse(ApiModel):
    authenticated: bool
    email: str
    csrf_token: str


class LogoutResponse(ApiModel):
    authenticated: bool


@router.get("/google/login")
def google_login(request: Request) -> RedirectResponse:
    manager = _manager(request)
    flow = manager.begin_login()
    response = RedirectResponse(flow.authorization_url, status_code=302)
    response.set_cookie(
        OAUTH_FLOW_COOKIE,
        flow.cookie_value,
        max_age=OAUTH_FLOW_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth/google/callback",
    )
    return response


@router.get("/google/callback", response_model=None)
def google_callback(
    request: Request,
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
) -> RedirectResponse:
    manager = _manager(request)
    flow_cookie = request.cookies.get(OAUTH_FLOW_COOKIE)
    if flow_cookie is None:
        raise ApiError(status_code=401, code="oauth_flow_invalid", message="Sign-in failed")
    try:
        session_cookie, _csrf_token = manager.complete_login(
            code=code,
            state=state,
            flow_cookie=flow_cookie,
        )
        identity = manager.authenticate(session_cookie)
    except AuthTokenError as error:
        raise ApiError(
            status_code=401,
            code="oauth_flow_invalid",
            message="Sign-in failed",
        ) from error
    if identity is None:
        raise ApiError(status_code=401, code="oauth_flow_invalid", message="Sign-in failed")
    response = RedirectResponse(
        request.app.state.container.settings.frontend_url,
        status_code=303,
    )
    response.set_cookie(
        SESSION_COOKIE,
        session_cookie,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(OAUTH_FLOW_COOKIE, path="/api/v1/auth/google/callback")
    return response


@router.get("/session", response_model=AuthSessionResponse)
def auth_session(owner: AuthenticatedOwner) -> AuthSessionResponse:
    return AuthSessionResponse(
        authenticated=True,
        email=owner.email,
        csrf_token=owner.csrf_token,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(_owner: AuthenticatedOwner) -> JSONResponse:
    payload = LogoutResponse(authenticated=False)
    response = JSONResponse(payload.model_dump(mode="json"))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def _manager(request: Request) -> AuthManager:
    manager: AuthManager | None = request.app.state.container.auth_manager
    if manager is None:
        raise ApiError(
            status_code=503,
            code="authentication_unavailable",
            message="Authentication is unavailable",
        )
    return manager
