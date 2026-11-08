import numpy as np

def robust_clean_laps(laps: list[dict]):
    valid = []
    excluded = []

    for lap in laps:
        duration = lap.get("lap_duration")
        if duration is None:
            excluded.append((lap, "missing_duration"))
            continue
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            excluded.append((lap, "invalid_duration"))
            continue
        if duration <= 0:
            excluded.append((lap, "non_positive_duration"))
            continue
        if lap.get("is_pit_out_lap") is True:
            excluded.append((lap, "pit_out_lap"))
            continue

        item = dict(lap)
        item["lap_duration"] = duration
        valid.append(item)

    if len(valid) < 5:
        return valid, excluded

    values = np.array([x["lap_duration"] for x in valid], dtype=float)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))

    threshold = median + 5.0 if mad == 0 else median + 5.0 * 1.4826 * mad

    cleaned = []
    for item in valid:
        if item["lap_duration"] <= threshold:
            cleaned.append(item)
        else:
            excluded.append((item, "robust_outlier"))

    return cleaned, excluded
