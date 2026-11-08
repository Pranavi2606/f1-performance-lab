from fastapi import APIRouter, HTTPException
from app.services import jolpica, openf1

router = APIRouter(prefix="/api", tags=["races"])

@router.get("/health")
def health():
    return {"status": "ok", "service": "f1-race-decision-intelligence"}

@router.get("/seasons/{year}/races")
def races(year: int):
    try:
        return jolpica.get_schedule(year)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jolpica request failed: {exc}")

@router.get("/races/{year}/{round_num}/overview")
def overview(year: int, round_num: int):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")

        results = jolpica.get_results(year, round_num)
        # OpenF1 historical coverage starts in 2023. Keep classification usable
        # for earlier seasons even when telemetry/session data does not exist.
        session = None
        drivers = []
        if year >= 2023:
            try:
                session = openf1.resolve_race_session(year, race["date"])
                drivers = openf1.get_drivers(session["session_key"])
            except Exception:
                session = None
                drivers = []

        return {"race": race, "results": results, "openf1Session": session, "drivers": drivers}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Race data request failed: {exc}")

@router.get("/races/{year}/{round_num}/driver/{driver_number}/raw")
def raw_driver_data(year: int, round_num: int, driver_number: int):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        session = openf1.resolve_race_session(year, race["date"])
        key = session["session_key"]
        return {
            "session": session,
            "laps": openf1.get_laps(key, driver_number),
            "stints": openf1.get_stints(key, driver_number),
            "pits": openf1.get_pits(key, driver_number),
            "carData": openf1.get_car_data(key, driver_number),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenF1 request failed: {exc}")
