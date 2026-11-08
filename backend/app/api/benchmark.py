"""Read only the benchmark the user has actually executed; never invent observations."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix='/api/benchmark', tags=['benchmark'])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_PATH = PROJECT_ROOT / 'results' / 'cross_event_real.json'

@router.get('/latest')
def latest_benchmark():
    if not BENCHMARK_PATH.is_file():
        raise HTTPException(status_code=404, detail='No executed benchmark yet. Run scripts/cross_event_benchmark.py or upload its JSON using the dashboard.')
    try:
        data = json.loads(BENCHMARK_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f'Benchmark file unreadable: {exc}')
    if not isinstance(data, dict) or data.get('source') != 'OpenF1' or not isinstance(data.get('events'), list):
        raise HTTPException(status_code=422, detail='Unexpected benchmark schema or source.')
    return data
