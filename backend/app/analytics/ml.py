import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error


def train_lap_model(points: list[dict]):
    """Chronological within-session baseline; cross-race validation is still required."""
    points = [p for p in points if all(p.get(k) is not None for k in ("lap", "tyre_age", "speed_trap", "lap_time"))]
    points = sorted(points, key=lambda p: int(p["lap"]))
    if len(points) < 24:
        return {"ready": False, "message": "Not enough complete lap observations (need at least 24) for a chronological hold-out evaluation."}
    X = np.array([[p["lap"], p["tyre_age"], p["speed_trap"]] for p in points], dtype=float)
    y = np.array([p["lap_time"] for p in points], dtype=float)
    split = max(12, int(len(points) * .75))
    if len(points) - split < 5:
        split = len(points) - 5
    X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]
    model = RandomForestRegressor(n_estimators=250, random_state=42, min_samples_leaf=2, n_jobs=-1)
    model.fit(X_train, y_train)
    prediction = model.predict(X_test)
    baseline_prediction = np.full_like(y_test, float(np.median(y_train)))
    return {
        "ready": True, "samples": len(points), "trainSamples": len(X_train), "testSamples": len(X_test),
        "r2": float(r2_score(y_test, prediction)) if len(y_test) > 1 else 0.0,
        "mae": float(mean_absolute_error(y_test, prediction)),
        "baselineMae": float(mean_absolute_error(y_test, baseline_prediction)),
        "evaluation": "Chronological 75/25 within-session holdout; later laps held out. not cross-race validation or cross-season generalisation.",
        "model": "RandomForestRegressor; 250 trees; min_samples_leaf=2; random_state=42",
        "featureImportance": [
            {"feature": "Lap number", "importance": float(model.feature_importances_[0])},
            {"feature": "Tyre age (derived from stint start)", "importance": float(model.feature_importances_[1])},
            {"feature": "Speed trap (km/h)", "importance": float(model.feature_importances_[2])},
        ],
    }
