"""Explicit-assumption public-data race scenario integration, not a vehicle physics twin."""
import numpy as np


def integrated_scenario(race_laps, base_lap_s, pit_loss_s, stops, tyre_slope_s,
                        energy_delta_s_per_lap=None, uncertainty_s=0.2, iterations=1000, seed=42):
    """No claim of ERS state: energy delta is an OPTIONAL user-specified lap-time effect."""
    if not 5 <= race_laps <= 100 or not 1 <= iterations <= 10000:
        raise ValueError("race_laps must be 5..100 and iterations 1..10000")
    if base_lap_s <= 0 or pit_loss_s < 0 or uncertainty_s < 0:
        raise ValueError("Invalid pace, pit loss or uncertainty")
    if energy_delta_s_per_lap is not None and abs(energy_delta_s_per_lap) > 10:
        raise ValueError("Energy scenario delta must be within +/-10 s/lap")
    stops = sorted(set(stops))
    if any(s <= 1 or s >= race_laps for s in stops): raise ValueError("Pit stops must be inside race distance")
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, uncertainty_s, size=(iterations, race_laps))
    age = 0; per_lap = []
    for lap in range(1, race_laps+1):
        if lap in stops: age = 0
        # Explicitly assume an energy lap-time offset rather than infer from acceleration proxy.
        energy = 0. if energy_delta_s_per_lap is None else energy_delta_s_per_lap
        per_lap.append(base_lap_s + tyre_slope_s*age + energy)
        age += 1
    total = np.sum(noise + np.array(per_lap), axis=1) + len(stops)*pit_loss_s
    return {"ready": True, "mean_race_s": float(np.mean(total)), "p05_s": float(np.percentile(total,5)),
            "p95_s": float(np.percentile(total,95)), "expected_lap_s": per_lap,
            "assumptions": {"base_lap_s": base_lap_s, "pit_loss_s": pit_loss_s,
                "stops": stops, "tyre_slope_s_per_lap": tyre_slope_s,
                "energy_delta_s_per_lap": energy_delta_s_per_lap,
                "noise_std_s": uncertainty_s, "iterations": iterations, "seed": seed},
            "energy_status": "user_assumption" if energy_delta_s_per_lap is not None else "unavailable_not_modelled",
            "limitations": "Integrated timing scenario only, NOT a physics-based vehicle digital twin. Tyre slope and energy-to-lap-time effect are assumed inputs, not derived ERS measurements. Noise intervals omit parameter uncertainty, traffic, safety cars, fuel and weather."}
