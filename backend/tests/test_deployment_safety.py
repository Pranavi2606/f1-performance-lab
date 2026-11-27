"""Prevent public deployment regressions without calling external race-data APIs."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app, allowed_browser_origins
from app.services import openf1
from app.api import benchmark


def test_cors_origin_config_does_not_allow_arbitrary_sites(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://f1-lab.vercel.app, https://preview.example.org/")
    origins = allowed_browser_origins()
    assert "https://f1-lab.vercel.app" in origins
    assert "https://preview.example.org" in origins
    assert "http://localhost:5174" in origins
    assert "*" not in origins
    assert "https://attacker.example" not in origins


def test_local_cors_preflight():
    response = TestClient(app).options("/api/health", headers={
        "Origin": "http://localhost:5174", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"


def test_missing_openf1_session_must_not_return_another_race():
    sessions = [{"session_key": 10, "date_start": "2024-03-02T15:00:00+00:00"},
                {"session_key": 20, "date_start": "2024-03-09T15:00:00+00:00"}]
    with patch.object(openf1, "get_race_sessions", return_value=sessions):
        assert openf1.resolve_race_session(2024, "2024-03-02")["session_key"] == 10
        with pytest.raises(ValueError, match="refusing a mismatched event"):
            openf1.resolve_race_session(2024, "2024-04-01")


def test_openf1_time_zone_boundary_is_accepted():
    sessions = [{"session_key": 99, "date_start": "2024-11-24T05:00:00+00:00"}]
    with patch.object(openf1, "get_race_sessions", return_value=sessions):
        assert openf1.resolve_race_session(2024, "2024-11-23")["session_key"] == 99


def test_executed_benchmark_is_bundled_for_serverless_backend():
    bundled = benchmark.BUNDLED_BENCHMARK_PATH
    assert bundled.is_file()
    report = json.loads(bundled.read_text(encoding="utf-8"))
    assert report["source"] == "OpenF1"
    assert sum(f["test_laps"] for event in report["events"]
               for f in event["predictive_benchmark"]["folds"]) == 47


def test_vercel_backend_entrypoint_exports_existing_api():
    from index import app as vercel_app
    assert vercel_app is app
    assert "/api/health" in vercel_app.openapi()["paths"]
