import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.api import benchmark


def test_latest_executed_file_is_exposed():
    path=Path(__file__).resolve().parents[2]/'results'/'cross_event_real.json'
    data=json.loads(path.read_text())
    assert data['source']=='OpenF1'
    assert sum(f['test_laps'] for e in data['events'] for f in e['predictive_benchmark']['folds'])==47
    response=TestClient(app).get('/api/benchmark/latest')
    assert response.status_code==200
    assert response.json()['events'][0]['circuit']=='Bahrain'


def test_missing_result_returns_unavailable(monkeypatch,tmp_path):
    monkeypatch.setattr(benchmark,'BENCHMARK_PATH',tmp_path/'missing.json')
    response=TestClient(app).get('/api/benchmark/latest')
    assert response.status_code==404
    assert 'No executed benchmark' in response.json()['detail']
