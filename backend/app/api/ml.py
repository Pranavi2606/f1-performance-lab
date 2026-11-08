from fastapi import APIRouter, HTTPException
from app.services import jolpica, openf1
from app.analytics.ml import train_lap_model

router = APIRouter(prefix="/api/ml", tags=["ml"])

@router.get("/lap-time/{year}/{round_num}/{driver_number}")
def lap_time_model(year:int, round_num:int, driver_number:int):
    try:
        schedule=jolpica.get_schedule(year)
        race=next((r for r in schedule if r["round"]==round_num),None)
        if not race: raise HTTPException(status_code=404, detail="Race not found")
        session=openf1.resolve_race_session(year,race["date"])
        key=session["session_key"]
        laps=openf1.get_laps(key,driver_number)
        stints=openf1.get_stints(key,driver_number)
        stint_age={}
        for s in stints:
            for lap in range(int(s["lap_start"]), int(s["lap_end"])+1):
                stint_age[lap]=max(0,lap-int(s["lap_start"]))
        points=[]
        for lap in laps:
            speed_trap = lap.get("st_speed") or lap.get("i1_speed")
            if lap.get("lap_duration") and speed_trap and lap.get("lap_number") in stint_age:
                points.append({
                    "lap":int(lap["lap_number"]),
                    "tyre_age":stint_age[int(lap["lap_number"])],
                    "speed_trap":float(speed_trap),
                    "lap_time":float(lap["lap_duration"])
                })
        return train_lap_model(points)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=502, detail=f"ML model failed: {exc}")
