from jwt import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.database import AsyncSessionLocal
from src.features.users.services.user_service import get_user_model_by_id_from_new_session
from src.shared.enums.enums import UserRole
from src.shared.utils.auth import get_user_from_request

PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/auth/sign-in"),
    ("POST", "/auth/sign-up"),
    ("POST", "/auth/refresh"),
    ("POST", "/auth/logout"),
    ("GET", "/docs"),
    ("GET", "/redoc"),
    ("GET", "/openapi.json"),
}

GUEST_ALLOWED_ROUTES = {
    ("GET", "/auth/profile"),
    ("GET", "/exams"),
    ("GET", "/exams/{exam_id}/questions"),
    ("GET", "/exams/{exam_id}/resolutions"),
    ("GET", "/exams/{exam_id}/resolutions/active"),
    ("GET", "/users"),
    ("POST", "/users"),
    ("PUT", "/users/{user_id}"),
    ("PATCH", "/users/{user_id}/role"),
    ("DELETE", "/users/{user_id}"),
    ("POST", "/exams/upload"),
    ("POST", "/exams/{exam_id}/resolutions"),
    ("DELETE", "/exams/{exam_id}"),
    ("GET", "/resolutions/{resolution_id}"),
    ("PUT", "/resolutions/{resolution_id}/questions/{question_id}/response"),
    ("POST", "/resolutions/{resolution_id}/questions/{question_id}/evaluate"),
    ("POST", "/resolutions/{resolution_id}/evaluate"),
    ("POST", "/resolutions/{resolution_id}/pause"),
    ("POST", "/resolutions/{resolution_id}/resume"),
    ("POST", "/resolutions/{resolution_id}/submit"),
}


def _normalize(path: str) -> str:
    return path[:-1] if len(path) > 1 and path.endswith("/") else path


def _matches_route(route_path: str, path: str) -> bool:
    route_parts = route_path.strip("/").split("/")
    path_parts = path.strip("/").split("/")

    if len(route_parts) != len(path_parts):
        return False

    return all(
        route_part == path_part or (route_part.startswith("{") and route_part.endswith("}"))
        for route_part, path_part in zip(route_parts, path_parts)
    )


def _is_guest_allowed_route(method: str, path: str) -> bool:
    return any(
        route_method == method and _matches_route(route_path, path) for route_method, route_path in GUEST_ALLOWED_ROUTES
    )


class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = _normalize(request.url.path)

        if method == "OPTIONS" or (method, path) in PUBLIC_ROUTES:
            return await call_next(request)

        try:
            user = get_user_from_request(request)
        except ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"success": False, "errors": ["Token expirado."], "data": None},
            )
        except (InvalidTokenError, ValueError):
            return JSONResponse(
                status_code=401,
                content={"success": False, "errors": ["Token inválido."], "data": None},
            )

        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "errors": ["Não autenticado."], "data": None},
            )

        if _is_guest_allowed_route(method, path):
            return await call_next(request)

        db_user = await get_user_model_by_id_from_new_session(user.id, session_factory=AsyncSessionLocal)

        if not db_user or db_user.role != UserRole.ADMIN:
            return JSONResponse(
                status_code=403,
                content={"success": False, "errors": ["Acesso restrito a administradores."], "data": None},
            )

        return await call_next(request)
