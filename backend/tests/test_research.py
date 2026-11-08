from datetime import datetime, timedelta, timezone
from app.analytics.research import energy_fingerprint, normalized_lap_segment


def stamp(t):
    return t.isoformat().replace('+00:00', 'Z')


def test_energy_fingerprint_detects_candidate_not_ers_claim():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i, speed in enumerate([180, 185, 190, 195, 200]):
        rows.append({"date": stamp(start + timedelta(seconds=i)), "speed": speed,
                     "throttle": 100, "brake": 0})
    result = energy_fingerprint(rows)
    assert result["candidate_count"] == 1
    assert "cannot identify ERS" in result["interpretation"]


def test_normalized_segment_uses_lap_timestamp_window():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    lap = {"lap_number": 1, "date_start": stamp(start), "lap_duration": 100}
    rows = []
    for i in range(81, 91):
        rows.append({"date": stamp(start + timedelta(seconds=i)), "speed": 250 + i / 10})
    result = normalized_lap_segment([lap], rows, .80, .90)
    assert result["ready"] is True
    assert result["laps_used"] == 1
    assert result["window"]["start_pct"] == .80

from app.analytics.research import contextual_tyre_analysis, corner_exit_repeatability
from app.analytics.simulation import compare_strategy_scenarios, simulate_strategy


def test_contextual_tyre_model_excludes_pit_out_and_reports_baseline():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    laps = []
    for i in range(1, 15):
        laps.append({"lap_number": i, "date_start": stamp(start + timedelta(seconds=90*(i-1))),
                     "lap_duration": 90 + .035*(i-1), "is_pit_out_lap": i == 1})
    stints = [{"stint_number": 1, "lap_start": 1, "lap_end": 14, "compound": "MEDIUM"}]
    weather = [{"date": stamp(start), "track_temperature": 34, "air_temperature": 25, "rainfall": 0}]
    result = contextual_tyre_analysis(laps, stints, weather, [])
    assert result["ready"] is True
    assert result["laps_used"] == 13
    assert result["laps_excluded"] == 1
    assert "context_adjusted" in result and "baseline_age_only" in result


def test_corner_exit_analysis_returns_clear_unavailable_without_location():
    result = corner_exit_repeatability([], [], [])
    assert result["ready"] is False
    assert "No location" in result["message"]


def test_strategy_simulation_is_reproducible():
    a = simulate_strategy(30, 90, .04, 22, [15], iterations=500, seed=7)
    b = simulate_strategy(30, 90, .04, 22, [15], iterations=500, seed=7)
    assert a["mean"] == b["mean"]
    assert a["seed"] == 7


def test_strategy_scenario_search_returns_ranked_candidates():
    result = compare_strategy_scenarios(race_laps=30, iterations=500)
    assert result["ready"] is True
    means = [x["mean_s"] for x in result["best_scenarios"]]
    assert means == sorted(means)
    assert result["best_scenarios"]
