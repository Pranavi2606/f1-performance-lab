from app.analytics.degradation import linear_fit, analyze_stints
from app.analytics.ml import train_lap_model


def test_linear_fit_recovers_slope():
    points = [{"lap": i, "time": 90 + 0.04 * i} for i in range(1, 8)]
    fit = linear_fit(points)
    assert fit is not None
    assert abs(fit["slope"] - 0.04) < 1e-9
    assert fit["rSquared"] > 0.999


def test_ml_uses_holdout_and_reports_samples():
    points = [
        {"lap": i, "tyre_age": i % 20, "speed_trap": 300 - (i % 7), "lap_time": 90 + .02 * (i % 20) - .01 * (i % 7)}
        for i in range(1, 81)
    ]
    result = train_lap_model(points)
    assert result["ready"] is True
    assert result["samples"] == 80
    assert result["testSamples"] == 20
    assert result["mae"] >= 0
    assert "not cross-race validation" in result["evaluation"]


def test_ml_rejects_small_samples():
    result = train_lap_model([{"lap": 1, "tyre_age": 1, "speed_trap": 300, "lap_time": 90}] * 10)
    assert result["ready"] is False
