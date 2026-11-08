# V6 validation and real data

## Implemented
- `/api/lab/calibration` reproducible synthetic 95% slope interval coverage, mean width, posterior CDF-rank histogram. This is NOT predictive PIT and does NOT validate F1 race forecasts.
- `/api/lab/composition/smooth` retrospective RTS smoothed state estimates; may use future laps and is not for prediction.
- `/api/lab/composition/filter` forward Kalman states; requires externally pre-specified `filter_q` and `filter_r`. T state uses observation at T, so it is not a T-before-observation forecast. Never fit q/r on the held-out race.
- `backend/scripts/cross_event_benchmark.py` fetches actual OpenF1 race lap/stint observations and produces descriptive event-level posterior slopes and intervals. This is NOT a transfer/generalization score.
- `backend/tests/test_v6.py` checks forward filter invariance when later observations change.

## Real-data acquisition
1. Internet-connected machine, Python environment, `pip install -r backend/requirements.txt`.
2. `cd backend && python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json`.
3. Confirm the event `status` is `computed`, and audit source and retained lap counts. Never report synthetic coverage as real-race coverage.
4. Run `uvicorn app.main:app --reload` and use `/docs` to call `/api/lab/composition-live` and `/api/lab/historical-evaluation` using actual OpenF1 session keys. OpenF1 API session metadata is the source of session keys.
5. Preserve the fetched response JSON, session keys, UTC dates, API version/access date, exclusion decisions, and metrics. If API blocks access, report unavailable and retry later; do not fill missing observations.

## Important methodological caveats
- Tyre slope is an association, not a measured physical tyre wear coefficient. Fuel load, compounds, traffic and weather confound it.
- Synthetic generator is intentionally simple and does not establish real-world reliability. Its 95% slope CI coverage is not equivalent to 95% predictive lap-time coverage.
- Filter states may be causal but can still be invalid predictors if tuning or normalization uses test data.
- The 3-state local quadratic smoother is exploratory; latent curvature is not proof of a tyre cliff.
- The cross-event script estimates separate per-event models; a true leave-one-event-out predictive transfer test remains to be completed.
- No proprietary Pirelli, CFD, battery state or ERS commands are available. No physics vehicle twin is claimed.

## Frontend build
`cd frontend && npm install && npm run build` on a machine with package registry access. This environment could not complete npm installation, so a successful production build is NOT claimed.
