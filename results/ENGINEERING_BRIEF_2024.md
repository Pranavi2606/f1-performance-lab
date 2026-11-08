# Historical F1 engineering research brief — 2024, driver #1

> **Evidence category:** Report generated from an executed benchmark JSON; this report generator does not fetch OpenF1 data or independently verify that the upstream file came from OpenF1.

**Input provenance:** user-executed cross_event_real.json, values pasted in conversation. **Reported feed:** OpenF1. **Events computed:** 3/3.

## Observed-model comparisons

The slope is a fitted *lap-time association with tyre age* in seconds per lap, **not a causal measurement of tyre wear**. The 95% interval is model-dependent.

| Event | Session key | Retained lap observations | Slope (s/lap) | 95% credible interval | Global-median inside CI? |
|---|---:|---:|---:|---|---|
| Bahrain | 9472 | 55 | +0.0689 | [+0.0336, +0.1059] | yes |
| Monaco | 9523 | 75 | -0.1035 | [-0.1415, -0.0639] | no |
| Belgium | 9574 | 42 | +0.0337 | [-0.0590, +0.1305] | yes |

## Held-out lap-time prediction — within-stint chronology

These are held-out **laps within each event**, not a model trained at one circuit and transferred to another. Compare MAE and RMSE against a training-median baseline.

| Event | Model | Held-out laps | MAE (seconds) | Pooled RMSE (seconds) |
|---|---|---:|---:|---:|
| Bahrain | unavailable (older benchmark JSON or insufficient stints) | — | — | — |
| Monaco | unavailable (older benchmark JSON or insufficient stints) | — | — | — |
| Belgium | unavailable (older benchmark JSON or insufficient stints) | — | — | — |

## Interpretation and confounding

- A positive slope is associated with increasing lap times; a negative slope with decreasing lap times. Neither uniquely identifies physical tyre degradation.
- **Fuel mass reduction**, pit stops and compound transitions, traffic, race-control periods, weather, track evolution and sampling biases can change apparent slopes.
- A credible interval excluding the median of three circuit estimates is **not** evidence on its own of a regime shift or generalization failure.
- With only three events, no out-of-event predictive generalization claim is supported.
- Steering angle, tyre surface condition, detailed brake pressure, battery state/ERS command and proprietary CFD data are **unavailable** from the standard OpenF1 car feed.
- The model's predictive-interval calibration on historical race laps is **not established** by the synthetic calibration audit.

## Evidence and reproducibility

- Source API documentation: https://openf1.org/ ; verify API provenance and terms before redistribution.
- Run `python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json` from `backend/` on a network-enabled machine.
- Generate this report with `python scripts/generate_engineering_brief.py --input ../results/cross_event_real.json --output ../results/ENGINEERING_BRIEF_2024.md`.
- Keep the original JSON alongside this Markdown to support reproducibility; timestamps and raw-response hashes have not yet been recorded.

## What we can safely say

The supplied benchmark records 3 successful circuit analyses using publicly described OpenF1 observations. **No out-of-sample prediction metrics appear in this input, so predictive accuracy cannot be claimed from it.**
