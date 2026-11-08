import requests

TIMEOUT = 20

def get_json(url: str, params: dict | None = None):
    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT,
        headers={"User-Agent": "F1-Race-Decision-Intelligence/1.0"},
    )
    response.raise_for_status()
    return response.json()
