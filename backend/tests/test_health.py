from unittest.mock import MagicMock

import pytest
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

client = TestClient(app)


def test_health_live():
    """Kiểm tra liveness endpoint luôn trả HTTP 200 và status ok."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_mock_success():
    """Kiểm tra readiness endpoint khi database hoạt động bình thường (mock)."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}
    finally:
        app.dependency_overrides.clear()


def test_health_ready_mock_failure():
    """Kiểm tra readiness endpoint khi database bị ngắt kết nối hoặc gặp sự cố (mock)."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = OperationalError("Connection refused", params=None, orig=Exception("DB down"))

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "error", "database": "unavailable"}
    finally:
        app.dependency_overrides.clear()


def test_health_ready_real_db_smoke():
    """Smoke test kết nối PostgreSQL thật qua cổng 5434 đang chạy trên Docker Compose."""
    import socket

    try:
        with socket.create_connection(("localhost", 5434), timeout=0.5):
            pass
    except OSError:
        pytest.skip("PostgreSQL trên cổng 5434 chưa chạy")

    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
