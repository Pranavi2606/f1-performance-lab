import pytest
from app.analytics.validation import audit_feed, evaluate_held_out_events
from app.analytics.bayesian import bayesian_tyre_model
from app.analytics.digital_twin import integrated_scenario
from app.main import app


def test_quality_duplicates_and_missing():
    data=[{"date":"2026-01-01T00:00:00Z","speed":120},{"date":"2026-01-01T00:00:00Z","speed":None}]
    r=audit_feed(data,("speed",))
    assert r["duplicate_timestamps"]==1 and r["missing_fields"]["speed"]==1


def test_bayes_no_fake_data():
    assert not bayesian_tyre_model([],[])["ready"]


def test_bayes_observed_trend():
    stints=[{"lap_start":1,"lap_end":24,"stint_number":1}]
    laps=[{"lap_number":i,"lap_duration":90+0.06*(i-1)} for i in range(1,25)]
    r=bayesian_tyre_model(laps,stints)
    assert r["ready"] and r["posterior_mean_s_per_lap"]>0


def test_scenario_reproducible_and_energy_unknown():
    a=integrated_scenario(20,90,20,[10],.05)
    b=integrated_scenario(20,90,20,[10],.05)
    assert a==b and a["energy_status"]=="unavailable_not_modelled"
    c=integrated_scenario(20,90,20,[10],.05,energy_delta_s_per_lap=-0.1)
    assert c["mean_race_s"]==pytest.approx(a["mean_race_s"]-2)


def test_holdout_requires_events():
    assert not evaluate_held_out_events([])["ready"]
    events=[{"event_id":str(i),"points":[{"age":j,"lap_time":90+i+j*.04} for j in range(10)]} for i in range(3)]
    assert len(evaluate_held_out_events(events)["folds"])==3


def test_routes_registered():
    paths=set(app.openapi()["paths"])
    assert "/api/lab/scenario" in paths and "/api/lab/held-out-events" in paths

def test_historical_route_registered():
    assert "/api/lab/historical-evaluation" in set(app.openapi()["paths"])
