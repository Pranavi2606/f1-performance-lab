# V4 implementation and evidence register

## New executable capabilities

1. **Data-quality audit:** counts missing required fields, duplicate and nonmonotonic timestamps, maximum gaps, median sampling interval, duplicate lap numbers. Reports absent feeds without filling gaps. Duplicate timestamps are a diagnostic, not automatically errors.
2. **Bayesian tyre-age regression:** conjugate Normal–Inverse-Gamma posterior for a pooled linear age coefficient with stint intercepts. Returns posterior slope, 95% credible interval and probability of positive slope, with explicit priors and deterministic sampling. **Not a state-space tyre model**, not a causal tyre-wear estimate. No weather/safety-car corrections in this Bayesian model.
3. **Integrated public-data timing scenario:** tyre-age slope, base pace, pit stops, optional assumed energy lap-time effect and stochastic lap-time variation. Returns reproducible race time and 5–95% noise interval. The energy term is **unavailable** unless a user explicitly supplies a scenario assumption. This is **not** a physics-based vehicle digital twin.
4. **Held-out event evaluation:** leave-one-event-out baseline linear tyre-age model vs training-median baseline, with MAE and RMSE. Accepts user-supplied observed event points (`POST /api/lab/held-out-events`) or fetches actual OpenF1 laps/stints for 3–6 explicit session keys and one driver (`POST /api/lab/historical-evaluation`). Does not automatically invent or pick events.
5. **React research view:** data coverage audit, Bayesian posterior summary, and scenario control with optional energy assumption.

## API examples

- `GET /api/research/{year}/{round}/{driver_number}` now includes `data_quality` and `bayesian_tyre_model`.
- `POST /api/lab/scenario` JSON: `{"race_laps":57,"base_lap_s":92,"pit_loss_s":22,"stops":[25],"tyre_slope_s_per_lap":0.04,"energy_delta_s_per_lap":null}`.
- `POST /api/lab/historical-evaluation` JSON: `{"session_keys":[1234,1235,1236],"driver_number":1}`. **Replace example session keys with real OpenF1 race session keys; example IDs are placeholders, not claimed events.**

## Explicit gaps

- No actual Pirelli/team tyre parameters, CFD, wind-tunnel, battery state, ERS command or measured energy-to-lap-time relationship.
- No validated Bayesian state-space filter or physics-based vehicle digital twin.
- No automatic cross-race validation run has been claimed. The historical evaluation endpoint requires actual accessible OpenF1 sessions and driver coverage; score interpretation requires review of race conditions and compound effects.
- Simulation noise interval **does not** incorporate tyre parameter uncertainty or weather/safety-car scenarios.
- No 2025/2026 event-by-event live coverage verification performed during this build.

## Reproducibility

Run `cd backend && python -m pytest -q`. Run frontend using `cd frontend && npm install && npm run build`; the frontend build requires dependencies to be available. Read `research/RESEARCH_PROTOCOL.md` for the existing research methodology.
