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


@lru_cache(maxsize=128)
def get_driver_lap_times(year: int, round_num: int, driver_number: int):
    """Retrieve observed race lap times as an honest backup when tyre stints are unavailable.

    Jolpica's driver-specific laps endpoint is distinct from OpenF1 tyre-stint telemetry.
    No compound, tyre age or degradation model can be reconstructed from these timings.
    """
    result = next((r for r in get_results(year, round_num)
                   if str(r.get("number")) == str(driver_number)), None)
    if result is None:
        return []
    driver_id = result["driverId"]
    # Most F1 races fit in a single driver-specific page (<=100 laps).
    data = get_json(f"{BASE_URL}/{year}/{round_num}/drivers/{driver_id}/laps.json",
                    {"limit": 100, "offset": 0})
    table = data.get("MRData", {}).get("RaceTable", {})
    races = table.get("Races", [])
    if not races:
        return []
    laps = []
    for entry in races[0].get("Laps", []):
        try:
            number = int(entry["number"])
            timing = next((t for t in entry.get("Timings", [])
                           if t.get("driverId") == driver_id), None)
            if timing is None:
                continue
            parts = timing["time"].split(":")
            duration = float(parts[-1]) + 60 * float(parts[-2]) if len(parts) == 2 else float(parts[-1])
            if number > 0 and 0 < duration < 600:
                laps.append({"lap": number, "time": duration})
        except (TypeError, KeyError, ValueError, IndexError):
            continue
    return sorted(laps, key=lambda x: x["lap"])
