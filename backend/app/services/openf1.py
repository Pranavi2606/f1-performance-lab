from functools import lru_cache
from datetime import datetime, timezone
from app.services.http import get_json

BASE_URL = "https://api.openf1.org/v1"

def _parse_dt(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

@lru_cache(maxsize=8)
def get_race_sessions(year: int):
    return get_json(f"{BASE_URL}/sessions", {"year": year, "session_name": "Race"})

def resolve_race_session(year: int, race_date: str):
    sessions = get_race_sessions(year)
    target = datetime.fromisoformat(race_date).replace(tzinfo=timezone.utc)
    if not sessions:
        raise ValueError(f"No OpenF1 race sessions found for {year}")
    return min(
        sessions,
        key=lambda s: abs((_parse_dt(s["date_start"]) - target).total_seconds())
    )

@lru_cache(maxsize=32)
def get_drivers(session_key: int):
    return get_json(f"{BASE_URL}/drivers", {"session_key": session_key})

@lru_cache(maxsize=64)
def get_laps(session_key: int, driver_number: int):
    return get_json(f"{BASE_URL}/laps", {"session_key": session_key, "driver_number": driver_number})

@lru_cache(maxsize=64)
def get_stints(session_key: int, driver_number: int):
    return get_json(f"{BASE_URL}/stints", {"session_key": session_key, "driver_number": driver_number})

@lru_cache(maxsize=64)
def get_pits(session_key: int, driver_number: int):
    return get_json(f"{BASE_URL}/pit", {"session_key": session_key, "driver_number": driver_number})

@lru_cache(maxsize=32)
def get_race_control(session_key: int):
    return get_json(f"{BASE_URL}/race_control", {"session_key": session_key})

@lru_cache(maxsize=32)
def get_weather(session_key: int):
    return get_json(f"{BASE_URL}/weather", {"session_key": session_key})

@lru_cache(maxsize=16)
def get_car_data(session_key: int, driver_number: int):
    return get_json(f"{BASE_URL}/car_data", {"session_key": session_key, "driver_number": driver_number})

@lru_cache(maxsize=16)
def get_location(session_key: int, driver_number: int):
    return get_json(f"{BASE_URL}/location", {"session_key": session_key, "driver_number": driver_number})

@lru_cache(maxsize=32)
def get_track_status(session_key: int):
    return get_json(f"{BASE_URL}/track_status", {"session_key": session_key})
