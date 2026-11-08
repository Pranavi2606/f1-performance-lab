from functools import lru_cache
from app.services.http import get_json

BASE_URL = "https://api.jolpi.ca/ergast/f1"

@lru_cache(maxsize=16)
def get_schedule(year: int):
    data = get_json(f"{BASE_URL}/{year}/races.json")
    races = data["MRData"]["RaceTable"]["Races"]
    return [
        {
            "season": int(r["season"]),
            "round": int(r["round"]),
            "raceName": r["raceName"],
            "date": r["date"],
            "time": r.get("time"),
            "circuitId": r["Circuit"]["circuitId"],
            "circuitName": r["Circuit"]["circuitName"],
            "locality": r["Circuit"]["Location"]["locality"],
            "country": r["Circuit"]["Location"]["country"],
        }
        for r in races
    ]

@lru_cache(maxsize=32)
def get_results(year: int, round_num: int):
    data = get_json(f"{BASE_URL}/{year}/{round_num}/results.json")
    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        return []
    results = races[0].get("Results", [])
    output = []
    for r in results:
        output.append({
            "position": int(r["position"]) if str(r.get("position", "")).isdigit() else None,
            "number": r.get("number"),
            "driverId": r["Driver"]["driverId"],
            "driver": f'{r["Driver"]["givenName"]} {r["Driver"]["familyName"]}',
            "constructor": r["Constructor"]["name"],
            "grid": int(r["grid"]) if str(r.get("grid", "")).isdigit() else None,
            "points": float(r.get("points", 0)),
            "status": r.get("status", "Unknown"),
            "laps": int(r["laps"]) if str(r.get("laps", "")).isdigit() else None,
        })
    return output
