from fastapi import APIRouter, HTTPException, Query, Response
from app.services import jolpica, openf1
from app.analytics.degradation import analyze_stints
from app.analytics.simulation import simulate_strategy, compare_strategy_scenarios
from app.analytics.debrief import build_driver_debrief, choose_lap
from app.analytics.debrief_artifacts import map_for_lap, render_pdf, render_markdown
from pydantic import BaseModel
from app.models.schemas import SimulationRequest

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/analytics/degradation/{year}/{round_num}/{driver_number}")
def degradation(year: int, round_num: int, driver_number: int):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        session = openf1.resolve_race_session(year, race["date"])
        key = session["session_key"]
        return {
            "driverNumber": driver_number,
            "sessionKey": key,
            "raceName": race["raceName"],
            "analysis": analyze_stints(openf1.get_laps(key, driver_number), openf1.get_stints(key, driver_number)),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Degradation analysis failed: {exc}")

@router.get("/analytics/race-control/{year}/{round_num}")
def race_control(year: int, round_num: int):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race: raise HTTPException(status_code=404, detail="Race not found")
        session = openf1.resolve_race_session(year, race["date"])
        return {"session": session, "events": openf1.get_race_control(session["session_key"])}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=502, detail=f"Race control request failed: {exc}")

@router.get("/analytics/laps/{year}/{round_num}/{driver_number}")
def driver_laps(year: int, round_num: int, driver_number: int):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race: raise HTTPException(status_code=404, detail="Race not found")
        key = openf1.resolve_race_session(year, race["date"])["session_key"]
        stints = openf1.get_stints(key, driver_number)
        output = []
        for lap in openf1.get_laps(key, driver_number):
            duration = lap.get('lap_duration')
            if not isinstance(duration, (int, float)) or duration <= 0 or lap.get('is_pit_out_lap') is True or not lap.get('date_start'):
                continue
            number = int(lap['lap_number'])
            stint = next((x for x in stints if int(x.get('lap_start',9999)) <= number <= int(x.get('lap_end',-1))), {})
            output.append({'lap_number': number, 'duration_s': round(float(duration),3), 'compound': stint.get('compound','UNKNOWN'),
                           'stint': stint.get('stint_number'), 'tyre_age_at_start': stint.get('tyre_age_at_start')})
        return {'session_key': key, 'driver_number': driver_number, 'laps': output}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=502, detail=f"Lap list unavailable: {exc}")


@router.get("/analytics/telemetry/{year}/{round_num}/{driver_number}")
def telemetry(year: int, round_num: int, driver_number: int, lap_number: int | None = None):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race: raise HTTPException(status_code=404, detail="Race not found")
        key = openf1.resolve_race_session(year, race['date'])['session_key']
        drivers = openf1.get_drivers(key)
        driver = next((d for d in drivers if int(d['driver_number']) == driver_number), None)
        if not driver: raise HTTPException(status_code=404, detail="Driver not found")
        from app.analytics.debrief import extract_lap_trace
        laps = openf1.get_laps(key, driver_number)
        trace = extract_lap_trace(openf1.get_car_data(key, driver_number), laps, lap_number)
        points = [{"distance": x['distance_m'], "progress_pct":x['progress_pct'], "speed":x['speed'],
                   "throttle":x['throttle'], "brake":x['brake'], "rpm":x['rpm'], "gear":x['gear']} for x in trace['points']]
        brakes = [p['brake'] for p in points]
        return {"session_key":key,"driver_number":driver_number,"full_name":driver.get('full_name',''),
                "team_name":driver.get('team_name',''),"laps":len(laps),"selected_lap":trace['lap_number'],
                "lap_time_s":trace['lap_time_s'],"avg_speed":round(sum(p['speed'] for p in points)/len(points),1),
                "max_speed":round(max(p['speed'] for p in points),1),
                "avg_throttle":round(sum(p['throttle'] for p in points)/len(points),1),
                "brake_events":sum(1 for i in range(1,len(brakes)) if brakes[i]>5 and brakes[i-1]<=5),
                "points":points,"measurement_note":"One selected lap. OpenF1 brake is binary; no calibrated brake pressure or steering angle."}
    except HTTPException:raise
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc))
    except Exception as exc:raise HTTPException(status_code=502,detail=f"Lap telemetry failed: {exc}")


class DebriefReportRequest(BaseModel):
    report: dict


@router.post("/analytics/debrief/export/{format_name}")
def export_debrief(format_name: str, payload: DebriefReportRequest):
    if format_name not in ("md", "pdf"):
        raise HTTPException(status_code=422, detail="format_name must be md or pdf")
    report = payload.report
    if not isinstance(report.get("comparisons"), list) or not isinstance(report.get("primary_driver"), dict):
        raise HTTPException(status_code=422, detail="Expected a generated driver debrief report")
    if format_name == 'md':
        return Response(content=render_markdown(report), media_type='text/markdown; charset=utf-8',
                        headers={'Content-Disposition':'attachment; filename="driver_debrief.md"'})
    return Response(content=render_pdf(report), media_type='application/pdf',
                    headers={'Content-Disposition':'attachment; filename="driver_debrief.pdf"'})


@router.get("/analytics/debrief/track/{year}/{round_num}/{driver_number}")
def driver_debrief_track(year: int, round_num: int, driver_number: int, lap_number: int | None = None, zones: str = ''):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race:
            raise HTTPException(status_code=404,detail="Race not found")
        key = openf1.resolve_race_session(year,race['date'])['session_key']
        lap = choose_lap(openf1.get_laps(key,driver_number),lap_number)
        bounds=[]
        for token in zones.split(';'):
            if not token: continue
            try:
                a,b=map(float,token.split(','))
                if 0<=a<b<=100:bounds.append([a,b])
            except (ValueError,TypeError):continue
        return map_for_lap(openf1.get_location(key,driver_number),lap,bounds[:20])
    except HTTPException:raise
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc))
    except Exception as exc:raise HTTPException(status_code=502,detail=f"Track-map failed: {exc}")

@router.get("/analytics/debrief/{year}/{round_num}/{primary_driver_number}")
def driver_debrief(year: int, round_num: int, primary_driver_number: int,
                   compare_driver_numbers: list[int] = Query(..., description="One or more comparison driver numbers"),
                   primary_lap_number: int | None = None, compare_lap_number: int | None = None):
    try:
        schedule = jolpica.get_schedule(year)
        race = next((r for r in schedule if r["round"] == round_num), None)
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        session = openf1.resolve_race_session(year, race["date"])
        key = session["session_key"]
        drivers = openf1.get_drivers(key)
        primary = next((d for d in drivers if int(d["driver_number"]) == primary_driver_number), None)
        if not primary:
            raise HTTPException(status_code=404, detail="Primary driver not found")
        comparison_payloads = []
        used = set()
        for number in compare_driver_numbers:
            if number == primary_driver_number or number in used:
                continue
            used.add(number)
            driver = next((d for d in drivers if int(d["driver_number"]) == number), None)
            if not driver:
                continue
            comparison_payloads.append({
                "driver": driver,
                "laps": openf1.get_laps(key, number),
                "car": openf1.get_car_data(key, number),
                "lap_number": compare_lap_number,
            })
        if not comparison_payloads:
            raise HTTPException(status_code=422, detail="At least one valid comparison driver different from the primary driver is required")
        result = build_driver_debrief(
            primary_driver=primary,
            primary_laps=openf1.get_laps(key, primary_driver_number),
            primary_car=openf1.get_car_data(key, primary_driver_number),
            comparison_payloads=comparison_payloads,
            primary_lap_number=primary_lap_number,
        )
        result.update({"session_key": key, "race_name": race["raceName"], "year": year, "round": round_num})
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Driver debrief failed: {exc}")

@router.post("/analytics/simulate")
def simulate(request: SimulationRequest):
    return simulate_strategy(
        race_laps=request.raceLaps, base_pace=request.basePace,
        degradation_per_lap=request.degradationPerLap, pit_loss=request.pitLoss,
        stops=request.stops, iterations=request.iterations,
    )


@router.get("/analytics/strategy-scenarios")
def strategy_scenarios(race_laps: int = 57, base_pace: float = 92.0, pit_loss: float = 22.0, iterations: int = 1500):
    if not 20 <= race_laps <= 100:
        raise HTTPException(status_code=422, detail="race_laps must be between 20 and 100")
    if iterations < 500 or iterations > 5000:
        raise HTTPException(status_code=422, detail="iterations must be between 500 and 5000")
    return compare_strategy_scenarios(race_laps=race_laps, base_pace=base_pace, pit_loss=pit_loss, iterations=iterations)
