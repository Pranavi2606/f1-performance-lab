"""Public F1 HTTP client with best-effort worker-local pacing and bounded retries."""
import threading
import time
import requests

TIMEOUT = 20
_lock = threading.Lock()
_next_at = 0.0


def _pace(url: str):
    global _next_at
    if not url.startswith("https://api.openf1.org/v1/"):
        return
    with _lock:
        delay = _next_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _next_at = time.monotonic() + 0.6


def get_json(url: str, params: dict | None = None):
    for attempt in range(2):
        _pace(url)
        response = requests.get(url, params=params, timeout=TIMEOUT,
                                headers={"User-Agent": "F1-Race-Decision-Intelligence/1.0"})
        if response.status_code == 429 and attempt == 0:
            try:
                delay = float(response.headers.get("Retry-After", "1.5"))
            except (TypeError, ValueError):
                delay = 1.5
            # Do not hold serverless invocations for a minute-long quota window.
            if 0 <= delay <= 3:
                time.sleep(max(1.0, delay))
                continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Exhausted request attempts")
