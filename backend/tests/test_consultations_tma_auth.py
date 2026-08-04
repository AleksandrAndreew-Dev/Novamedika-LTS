"""
Regression tests for consultation endpoints auth + route ordering.

Verifies that:
1. All /consultations/* endpoints use get_current_user_jwt_or_tma (not JWT-only).
2. /consultations/stats is registered BEFORE /consultations/{consultation_id}
   to prevent FastAPI from matching "stats" as a UUID path param (400).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth.auth import get_current_user_jwt, get_current_user_jwt_or_tma
from routers.qa import router


def test_consultation_routes_use_tma_aware_auth_dependency():
    """All /consultations/* endpoints must use get_current_user_jwt_or_tma."""
    routes = {
        route.path: route.dependant.dependencies
        for route in router.routes
        if getattr(route, "path", "").startswith("/consultations")
    }

    required_paths = [
        "/consultations/",
        "/consultations/{consultation_id}",
        "/consultations/stats",
        "/consultations/{consultation_id}/messages",
    ]

    for path in required_paths:
        assert path in routes, f"Route {path} not found in router"
        dependencies = routes[path]
        assert any(dep.call is get_current_user_jwt_or_tma for dep in dependencies), (
            f"Route {path} does not use get_current_user_jwt_or_tma — "
            f"it only accepts JWT, not TMA (Telegram Web App)"
        )


def test_stats_route_not_jwt_only():
    """stats endpoint must NOT depend on get_current_user_jwt (JWT-only)."""
    routes = {
        route.path: route.dependant.dependencies
        for route in router.routes
        if getattr(route, "path", "").startswith("/consultations")
    }
    dependencies = routes["/consultations/stats"]
    assert not any(
        dep.call is get_current_user_jwt for dep in dependencies
    ), "/consultations/stats still uses get_current_user_jwt (JWT-only)"


def test_stats_route_registered_before_param_route():
    """
    In FastAPI, /consultations/{consultation_id} defined before
    /consultations/stats causes "stats" to be matched as a UUID
    path param → 400 Bad Request.

    Verify that the stats route appears BEFORE the parameterized route.
    """
    route_paths_in_order = [
        route.path
        for route in router.routes
        if getattr(route, "path", "").startswith("/consultations")
    ]

    stats_idx = route_paths_in_order.index("/consultations/stats")
    param_idx = route_paths_in_order.index("/consultations/{consultation_id}")

    assert stats_idx < param_idx, (
        f"Route ordering bug: /consultations/stats (index {stats_idx}) must be "
        f"registered BEFORE /consultations/{{consultation_id}} (index {param_idx}) "
        f"to prevent 'stats' from being matched as a UUID param"
    )
