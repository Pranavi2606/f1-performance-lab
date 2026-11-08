"""Stateless, auditable research endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.analytics.digital_twin import integrated_scenario
from app.analytics.validation import evaluate_held_out_events

router = APIRouter(prefix="/api/lab", tags=["validation-and-simulation"])

class Scenario(BaseModel):
    race_laps: int = Field(default=57, ge=5, le=100)
    base_lap_s: float = Field(default=92., gt=0)
    pit_loss_s: float = Field(default=22., ge=0)
    stops: list[int] = Field(default_factory=lambda: [25])
    tyre_slope_s_per_lap: float = Field(default=0.04, ge=-2, le=2)
    energy_delta_s_per_lap: float | None = Field(default=None, ge=-10, le=10)
    uncertainty_s: float = Field(default=0.2, ge=0, le=10)
    iterations: int = Field(default=1000, ge=1, le=10000)
    seed: int = 42

@router.post("/scenario")
def scenario(payload: Scenario):
    try: return integrated_scenario(**payload.model_dump())
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc))

class Event(BaseModel):
    event_id: str
    points: list[dict]

class Evaluation(BaseModel):
    events: list[Event] = Field(min_length=3, max_length=30)

@router.post("/held-out-events")
def held_out_events(payload: Evaluation):
    if len({e.event_id for e in payload.events}) != len(payload.events):
        raise HTTPException(status_code=422, detail="Each event_id must be unique")
    return evaluate_held_out_events([e.model_dump() for e in payload.events])

class HistoricalEvaluation(BaseModel):
    session_keys: list[int] = Field(min_length=3, max_length=6)
    driver_number: int = Field(ge=1, le=999)

@router.post("/historical-evaluation")
def historical_evaluation(payload: HistoricalEvaluation):
    """Fetch actual OpenF1 lap/stint observations for explicitly selected race sessions."""
    from app.services import openf1
    if len(set(payload.session_keys)) != len(payload.session_keys):
        raise HTTPException(status_code=422, detail="session_keys must be distinct")
    events=[]; errors=[]
    for key in payload.session_keys:
        try:
            laps=openf1.get_laps(key, payload.driver_number)
            stints=openf1.get_stints(key, payload.driver_number)
            by_lap={}
            for stint in stints:
                for n in range(int(stint["lap_start"]),int(stint["lap_end"])+1):
                    by_lap[n]=stint
            points=[]
            for lap in laps:
                try:
                    n=int(lap["lap_number"]); t=float(lap["lap_duration"])
                    if n not in by_lap or not (0<t<300) or lap.get("is_pit_out_lap"): continue
                    points.append({"age":n-int(by_lap[n]["lap_start"]),"lap_time":t})
                except (KeyError, ValueError, TypeError): continue
            events.append({"event_id":str(key),"points":points})
        except Exception as exc:
            errors.append({"session_key":key,"error":str(exc)})
    result=evaluate_held_out_events(events)
    result["source"]="OpenF1 observed laps and stints"
    result["session_coverage"]=[{"session_key":int(e["event_id"]),"valid_laps":len(e["points"])} for e in events]
    result["fetch_errors"]=errors
    result["filter_note"]="Excludes missing/invalid duration and pit-out laps. Does not exclude safety-car/traffic laps; scores are exploratory."
    return result

class CompositionRequest(BaseModel):
    laps: list[dict]
    stints: list[dict]
    car: list[dict] | None = None
    location: list[dict] | None = None
    weather: list[dict] | None = None
    race_control: list[dict] | None = None
    scenario: dict | None = None

@router.post('/composition')
def composition(payload: CompositionRequest):
    from app.analytics.composition import compose_public_data_report
    return compose_public_data_report(**payload.model_dump())

class LiveCompositionRequest(BaseModel):
    session_key: int = Field(gt=0)
    driver_number: int = Field(ge=1,le=999)
    include_telemetry: bool = False
    scenario: dict | None = None

@router.post('/composition-live')
def composition_live(payload: LiveCompositionRequest):
    from app.analytics.composition import compose_public_data_report
    from app.services import openf1
    try:
        laps=openf1.get_laps(payload.session_key,payload.driver_number)
        stints=openf1.get_stints(payload.session_key,payload.driver_number)
        car=openf1.get_car_data(payload.session_key,payload.driver_number) if payload.include_telemetry else None
        return compose_public_data_report(laps,stints,car=car,scenario=payload.scenario,
                                         source=f'OpenF1 session={payload.session_key} driver={payload.driver_number}')
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f'Upstream public feed unavailable: {exc}')


class CalibrationRequest(BaseModel):
    runs: int = Field(default=500, ge=10, le=10000)
    seed: int = 42
    scenario: str = 'stable'

@router.post('/calibration')
def calibration(payload: CalibrationRequest):
    from app.analytics.evaluation import calibration_report
    try: return calibration_report(payload.runs, payload.seed, payload.scenario)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc))

class ModeCompositionRequest(CompositionRequest):
    filter_q: float | None = Field(default=None, gt=0)
    filter_r: float | None = Field(default=None, gt=0)

@router.post('/composition/smooth')
def composition_smooth(payload: CompositionRequest):
    from app.analytics.composition import compose_public_data_report
    return compose_public_data_report(**payload.model_dump(), state_mode='smooth')

@router.post('/composition/filter')
def composition_filter(payload: ModeCompositionRequest):
    from app.analytics.composition import compose_public_data_report
    data=payload.model_dump()
    q=data.pop('filter_q'); r=data.pop('filter_r')
    if q is None or r is None:
        raise HTTPException(status_code=422, detail='Specify q/r from independent training data; tuning on this stint would leak future information')
    return compose_public_data_report(**data,state_mode='filter',filter_q=q,filter_r=r)
