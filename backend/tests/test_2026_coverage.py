"""Network-free contract test for 2026 session manifest ingestion."""
import importlib.util
import json
from pathlib import Path

def test_offline_coverage(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_2026_coverage.py"
    spec = importlib.util.spec_from_file_location("build_2026_coverage", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "sessions_2026.json").write_text(json.dumps([
        {"session_name":"Race","session_key":999,"meeting_key":100,"meeting_name":"Sample","location":"Test","country_name":"Test","date_start":"2026-11-08T15:00:00+00:00","date_end":"2026-11-08T17:00:00+00:00"},
        {"session_name":"Qualifying","session_key":998,"date_start":"2026-11-07T15:00:00+00:00"}
    ]), encoding="utf-8")
    data = module.make_manifest([2026], offline=tmp_path)
    rows = data["seasons"]["2026"]
    assert len(rows) == 1
    assert rows[0]["session_key"] == 999
    assert rows[0]["coverage"]["car_data"] == "not_checked"
    assert data["method"].startswith("OpenF1 Race sessions only")
