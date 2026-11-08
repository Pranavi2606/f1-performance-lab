# V8 — executed-result comparison dashboard

## What's delivered

- New **Research Results** page in the React sidebar; it does not depend on the selected Grand Prix or Jolpica season dropdown.
- Grouped bar chart: **per-event** held-out MAE or RMSE for median, OLS, piecewise-BIC and Bayesian posterior mean.
- Line chart: **per-stint** held-out errors in race/stint order (categorical, *not* a continuous trajectory).
- Descriptive fitted slopes and precise 95% credible intervals displayed separately from predictive scores.
- A pooled error table. MAE = sum(n_fold * MAE_fold)/sum(n_fold); RMSE = sqrt(sum(n_fold * RMSE_fold²)/sum(n_fold)). Aggregation respects each model's available folds.
- Backend `GET /api/benchmark/latest` reads only `results/cross_event_real.json` from the project directory. No new data is fabricated.
- An **Import JSON** control lets users directly load `cross_event_real.json` from any folder on their computer without copying into the app.
- Bundled `results/cross_event_real.json` is transcribed from the user's **executed** 2024 Bahrain/Monaco/Belgium benchmark pasted in the conversation (8 folds, 47 test laps), not simulated and not independently re-fetched in this environment. The raw lap observations are not bundled.

## Start

```powershell
# Terminal 1 (from project root)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 (from project root)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 -> **Research Results**. The default view uses the bundled executed report. To refresh from a new benchmark:

```powershell
# From backend/
python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json
```

Return to the Research Results page and click **RELOAD SAVED RESULT**, or import an existing JSON file with **IMPORT JSON**. This is a saved-result dashboard, *not* a live telemetry stream.

## Statistical interpretation

- 172 reported race-lap records and 47 held-out test-lap observations across 8 within-stint chronological folds. Training samples differ by fold. These are not 172 independent test samples.
- The backend script does not yet demonstrate generalization across held-out circuits. Within-stint held-out error is an important but narrower test.
- Piecewise-BIC is missing in Belgium stint 1, so its total pooled error is **not directly comparable** to the other models without restricting all models to identical folds.
- Fitted slope intervals are credible intervals *for slope estimates*, not predictive intervals for future lap times.
- The 2024 JSON results came from the user's local OpenF1 execution. This package does not include raw API snapshots or code-version hashes needed for independent reproducibility.
- No proprietary tyre, steering-angle, battery-state or ERS command measurements are implied.

## Verification

- Backend: `python -m pytest -q` passed, including checks that the saved JSON contains exactly 47 held-out test-lap observations and returns a 404 when unavailable.
- Frontend: dependency installation timed out in this execution environment, so **the production build was not verified**. Run `npm install && npm run build` locally. No claim of a verified frontend build is made.

## Evidence from the supplied 2024 run (not independently re-fetched)

Pooled per-model scores from the user's execution:

| Model | Held-out test laps | Pooled MAE (s) | Pooled RMSE (s) |
|---|---:|---:|---:|
| Median baseline | 47 | 0.996 | 1.421 |
| OLS | 47 | 1.418 | 2.029 |
| Bayesian posterior mean | 47 | 1.380 | 1.951 |
| Piecewise-BIC | 44 | 0.686 | 1.103 |

When compared with the median **on exactly the same folds**, piecewise-BIC lowers MAE by about 27.7% over 44 laps. OLS and Bayesian perform worse than the median on the full 47 laps. This is an observational performance comparison on eight small hold-out folds, not an established generalization claim. The interface computes these comparisons directly from whichever JSON is loaded, rather than hardcoding them.
