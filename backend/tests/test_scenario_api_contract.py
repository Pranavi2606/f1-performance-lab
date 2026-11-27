"""Ensure the public scenario API maps the documented request field to the model."""
from app.api.lab import Scenario, scenario


def test_scenario_accepts_ui_payload():
    payload = Scenario(race_laps=57, base_lap_s=92, pit_loss_s=22, stops=[25],
                       tyre_slope_s_per_lap=0.04, energy_delta_s_per_lap=None,
                       iterations=1000, seed=42)
    result=scenario(payload)
    assert result["ready"] is True
    assert result["assumptions"]["tyre_slope_s_per_lap"] == 0.04
    assert result["energy_status"] == "unavailable_not_modelled"
