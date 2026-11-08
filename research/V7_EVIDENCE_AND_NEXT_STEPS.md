# V7: evidence-first validation

## Implemented
- Added model-level within-stint chronological out-of-sample metrics to `scripts/cross_event_benchmark.py`. These are **not** cross-event transfer metrics, and do not prove real-world predictive calibration.
- Added a reproducible Markdown engineering brief generator that consumes the actual run JSON and refuses to create missing prediction results.
- Included an attributed snapshot of the user's executed 2024 Bahrain/Monaco/Belgium benchmark. This snapshot was provided in the conversation and **was not independently refetched by the ZIP author**.
- Added tests for absence of fabricated metrics and weighted MAE/RMSE aggregation.

## Run with live public data
From `backend/`:

```powershell
python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json
python scripts/generate_engineering_brief.py --input ../results/cross_event_real.json --output ../results/ENGINEERING_BRIEF_LIVE.md
python -m pytest -q
```

Compare the new `predictive_benchmark` scores **per event** against the training-median baseline. An additional event-level leave-one-circuit-out experimental design would be needed to claim transfer generalization.

## Outstanding validity issues
- Pit-out exclusions and lap duration screening are basic; race-control/traffic/weather/fuel effects are not causally identified by the benchmark.
- Random per-stint intervals and pooled tyre coefficients are not calibrated actual tyre-wear readings.
- A forward Kalman filter on within-stint data is not automatically a genuinely forward *forecast* (state posterior uses current observation). The RTS smoother is retrospective only.
- Validation must include published session IDs, raw extraction timestamps and reproducible version tags for research-paper-grade work.
- Steering angle and true oversteer classification are unavailable in the public feed.
