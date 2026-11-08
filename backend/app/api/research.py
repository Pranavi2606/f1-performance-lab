from fastapi import APIRouter, HTTPException, Query
from app.services import jolpica, openf1
from app.analytics.research import energy_fingerprint, normalized_lap_segment, corner_exit_repeatability, contextual_tyre_analysis
from app.analytics.validation import audit_session
from app.analytics.bayesian import bayesian_tyre_model

router = APIRouter(prefix="/api/research", tags=["research"])


def _session(year: int, round_num: int):
    schedule = jolpica.get_schedule(year)
    race = next((r for r in schedule if r["round"] == round_num), None)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found in selected season")
    try:
        session = openf1.resolve_race_session(year, race["date"])
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"No matching OpenF1 race session: {exc}")
    return race, session


@router.get("/compare/{year}/{round_num}")
def compare_energy_drivers(year: int, round_num: int,
                           driver_numbers: list[int] = Query(..., min_length=2, max_length=4)):
    """Compare observable acceleration fingerprints for 2–4 selected drivers."""
    try:
        if len(set(driver_numbers)) != len(driver_numbers):
            raise HTTPException(status_code=422, detail="driver_numbers must be unique")
        race, session = _session(year, round_num)
        key = int(session["session_key"])
        drivers = openf1.get_drivers(key)
        by_number = {int(d["driver_number"]): d for d in drivers}
        comparisons = []
        for number in driver_numbers:
            if number not in by_number:
                raise HTTPException(status_code=404, detail=f"Driver {number} not found in OpenF1 session")
            result = energy_fingerprint(openf1.get_car_data(key, number))
            comparisons.append({"driver_number": number,
                                "driver_name": by_number[number].get("full_name", str(number)),
                                "sample_count": result["sample_count"],
                                "candidate_count": result["candidate_count"],
                                "total_candidate_seconds": result["total_candidate_seconds"],
                                "interpretation": result["interpretation"]})
        return {"race_name": race["raceName"], "session": session,
                "method": "same thresholds applied to each selected driver's public car_data feed",
                "drivers": comparisons,
                "warning": "This compares observable acceleration proxies, not ERS/MGU-K deployment, energy-store state or car performance. Driver, traffic, tow, DRS, setup and conditions are confounders."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Driver comparison failed: {exc}")


@router.get("/{year}/{round_num}/{driver_number}")
def research_bundle(year: int, round_num: int, driver_number: int,
                    segment_start: float = Query(.80, ge=0, lt=1),
                    segment_end: float = Query(.90, gt=0, le=1)):
    """Return telemetry proxies, curvature-derived corner-like exits and contextual tyre analysis."""
    if segment_start >= segment_end:
        raise HTTPException(status_code=422, detail="segment_start must be below segment_end")
    try:
        race, session = _session(year, round_num)
        key = int(session["session_key"])
        drivers = openf1.get_drivers(key)
        driver = next((d for d in drivers if int(d["driver_number"]) == driver_number), None)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found in OpenF1 session")
        laps = openf1.get_laps(key, driver_number)
        car = openf1.get_car_data(key, driver_number)
        stints = openf1.get_stints(key, driver_number)
        # Optional context feeds can be absent for a session; never fabricate replacements.
        try: weather = openf1.get_weather(key)
        except Exception: weather = []
        try: race_control = openf1.get_race_control(key)
        except Exception: race_control = []
        # Location is high-volume; fetch only for the selected driver and explicit research run.
        try: location = openf1.get_location(key, driver_number)
        except Exception: location = []
        return {"year": year, "round": round_num, "race_name": race["raceName"],
                "session": session, "driver_number": driver_number,
                "driver_name": driver.get("full_name", str(driver_number)),
                "energy_fingerprint": energy_fingerprint(car),
                "corner_exit_repeatability": corner_exit_repeatability(laps, location, car),
                "normalized_segment_repeatability": normalized_lap_segment(laps, car, segment_start, segment_end),
                "contextual_tyre_analysis": contextual_tyre_analysis(laps, stints, weather, race_control),
                "bayesian_tyre_model": bayesian_tyre_model(laps, stints),
                "data_quality": audit_session(laps, stints, car, location, weather, race_control),
                "data_source": "OpenF1 public API",
                "data_provenance": {"laps": {"endpoint":"OpenF1 /laps", "available":bool(laps)},
                                    "stints": {"endpoint":"OpenF1 /stints", "available":bool(stints)},
                                    "car_telemetry": {"endpoint":"OpenF1 /car_data", "available":bool(car)},
                                    "location": {"endpoint":"OpenF1 /location", "available":bool(location)},
                                    "weather": {"endpoint":"OpenF1 /weather", "available":bool(weather)},
                                    "race_control": {"endpoint":"OpenF1 /race_control", "available":bool(race_control)}},
                "coverage_note": "OpenF1 historical telemetry coverage begins in 2023; 2026 results depend on sessions already published by the API. Missing endpoints are reported as unavailable, not imputed."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research analysis failed: {exc}")
