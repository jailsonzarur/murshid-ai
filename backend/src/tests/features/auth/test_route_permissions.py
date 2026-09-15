from __future__ import annotations

from fastapi.routing import APIRoute

from src.features.auth.middleware import (
    GUEST_ALLOWED_ROUTES,
    PUBLIC_ROUTES,
    _is_guest_allowed_route,
)
from src.main import app

ADMIN_ONLY = {
    ("GET", "/users"),
    ("POST", "/users"),
    ("PUT", "/users/{user_id}"),
    ("PATCH", "/users/{user_id}/role"),
    ("DELETE", "/users/{user_id}"),
}


def _registered() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            found.add((method, route.path))
    return found


class TestRoutePermissions:
    def test_every_route_is_classified(self):
        """Rota nova que ninguém classifica cai no default de ADMIN e some para o
        usuário comum, sem erro em teste nenhum. Já aconteceu duas vezes."""
        unclassified = {
            (method, path)
            for method, path in _registered()
            if (method, path) not in PUBLIC_ROUTES
            and (method, path) not in ADMIN_ONLY
            and not _is_guest_allowed_route(method, path)
        }

        assert unclassified == set(), (
            "rotas sem classificação de permissão — adicione a GUEST_ALLOWED_ROUTES "
            f"no middleware, ou a ADMIN_ONLY neste teste: {sorted(unclassified)}"
        )

    def test_the_allowlist_has_no_dead_entries(self):
        registered = _registered()
        dead = {
            (method, path)
            for method, path in GUEST_ALLOWED_ROUTES
            if (method, path) not in registered
        }

        assert dead == set(), f"rotas na allowlist que não existem mais: {sorted(dead)}"

    def test_the_lecture_actions_are_reachable_by_a_guest(self):
        for method, path in (
            ("POST", "/lectures/{lecture_id}/mindmap"),
            ("POST", "/lectures/{lecture_id}/guided-summary"),
            ("GET", "/lectures/{lecture_id}/guided-citations"),
            ("PATCH", "/lectures/{lecture_id}/subject"),
        ):
            assert _is_guest_allowed_route(method, path.replace("{lecture_id}", "abc"))
