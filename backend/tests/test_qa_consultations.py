import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth.auth import get_current_user_jwt_or_tma
from routers.qa import build_consultations_query, router


def test_build_consultations_query_with_valid_eager_loading():
    user_id = uuid.uuid4()

    query = build_consultations_query(
        user_id=user_id,
        status_filter="answered",
        page=2,
        limit=5,
    )

    compiled = str(query)

    assert "qa_questions" in compiled
    assert "ORDER BY" in compiled
    assert "LIMIT" in compiled
    assert "OFFSET" in compiled


def test_consultation_routes_use_tma_aware_auth_dependency():
    routes = {
        route.path: route.dependant.dependencies
        for route in router.routes
        if getattr(route, "path", "").startswith("/consultations")
    }

    for path in [
        "/consultations/",
        "/consultations/{consultation_id}",
        "/consultations/{consultation_id}/messages",
    ]:
        dependencies = routes[path]
        assert any(dep.call is get_current_user_jwt_or_tma for dep in dependencies)
