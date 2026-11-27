"""Live Stint Analysis must not mislabel lap-time fallback as tyre degradation."""
from unittest.mock import patch
from fastapi import HTTPException
from app.api.analytics import degradation
from app.services.jolpica import get_driver_lap_times


def test_stint_openf1_outage_uses_verified_laps():
    with patch("app.api.analytics.jolpica.get_schedule", return_value=[{"round":1,"date":"2024-03-02","raceName":"Bahrain Grand Prix"}]), \
         patch("app.api.analytics.openf1.resolve_race_session", side_effect=RuntimeError("401 from OpenF1")), \
         patch("app.api.analytics.jolpica.get_driver_lap_times", return_value=[{"lap":1,"time":94.5},{"lap":2,"time":92.1}]):
        result=degradation(2024,1,1)
    assert result["source"]=="Jolpica"
    assert result["mode"]=="lap_times_only"
    assert result["analysis"]["stints"]==[]
    assert result["lapTiming"][0]["time"]==94.5
    assert "no compound" in result["note"]


def test_stint_openf1_outage_with_no_laps_returns_503_not_fabrication():
    with patch("app.api.analytics.jolpica.get_schedule", return_value=[{"round":1,"date":"2024-03-02","raceName":"Bahrain Grand Prix"}]), \
         patch("app.api.analytics.openf1.resolve_race_session", side_effect=RuntimeError("429 from OpenF1")), \
         patch("app.api.analytics.jolpica.get_driver_lap_times", return_value=[]):
        try:
            degradation(2024,1,1)
        except HTTPException as exc:
            assert exc.status_code == 503
        else:
            assert False, "Expected explicit upstream unavailability"


def test_jolpica_driver_lap_parsing():
    sample={"MRData":{"RaceTable":{"Races":[{"Laps":[
      {"number":"1","Timings":[{"driverId":"verstappen","time":"1:35.000"}]},
      {"number":"2","Timings":[{"driverId":"verstappen","time":"1:34.120"}]}
    ]}]}}}
    with patch("app.services.jolpica.get_results", return_value=[{"number":"1","driverId":"verstappen"}]), \
         patch("app.services.jolpica.get_json", return_value=sample):
        get_driver_lap_times.cache_clear()
        data=get_driver_lap_times(2024,1,1)
        get_driver_lap_times.cache_clear()
    assert data==[{"lap":1,"time":95.0},{"lap":2,"time":94.12}]
