import numpy as np
from app.analytics.cleaning import robust_clean_laps

def linear_fit(points: list[dict]):
    x = np.array([p["lap"] for p in points], dtype=float)
    y = np.array([p["time"] for p in points], dtype=float)

    if len(points) < 3 or np.ptp(x) == 0:
        return None

    slope, intercept = np.polyfit(x, y, 1)
    prediction = slope * x + intercept
    ss_res = float(np.sum((y - prediction) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "rSquared": float(r2),
        "n": len(points),
    }

def analyze_stints(laps: list[dict], stints: list[dict]):
    cleaned, excluded = robust_clean_laps(laps)
    by_lap = {int(x["lap_number"]): x for x in cleaned}
    analyses = []

    for stint in sorted(stints, key=lambda s: s["stint_number"]):
        start = int(stint["lap_start"])
        end = int(stint["lap_end"])
        points = [
            {"lap": lap_no, "time": float(by_lap[lap_no]["lap_duration"])}
            for lap_no in range(start, end + 1)
            if lap_no in by_lap
        ]

        fit = linear_fit(points)
        if not fit:
            continue

        slope = fit["slope"]
        if slope > 0.05:
            recommendation = "HIGH_DEG"
            message = "High degradation signal; a shorter stint or earlier stop may be worth evaluating."
        elif slope > 0.02:
            recommendation = "MED_DEG"
            message = "Moderate degradation; tyre management and undercut timing should be evaluated."
        else:
            recommendation = "LOW_DEG"
            message = "Low degradation signal; extending the stint may be viable if traffic and tyre temperature allow."

        analyses.append({
            "stintNumber": int(stint["stint_number"]),
            "compound": stint.get("compound", "UNKNOWN"),
            "lapStart": start,
            "lapEnd": end,
            "tyreAgeAtStart": stint.get("tyre_age_at_start"),
            "degradationRate": slope,
            "intercept": fit["intercept"],
            "rSquared": fit["rSquared"],
            "lapsAnalyzed": fit["n"],
            "recommendation": recommendation,
            "message": message,
            "points": points,
        })

    return {
        "cleanLapCount": len(cleaned),
        "excludedLapCount": len(excluded),
        "excludedReasons": [
            {"lap": int(item.get("lap_number", 0)), "reason": reason}
            for item, reason in excluded
        ],
        "stints": analyses,
    }
