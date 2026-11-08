# V11 — release candidate verification and outstanding gates

**Research result status:** `results/cross_event_real.json` is a user-executed OpenF1 three-event benchmark. It contains 2024 Bahrain, Monaco and Belgium, 172 reported lap records, 47 held-out test laps across eight within-stint chronological folds. These are NOT cross-circuit forecast tests. The fitted slopes are lap-time associations, not isolated physical tyre-wear rates. The resulting aggregate charts compare each model only on folds where that model is available.

**Corrected integration:**
- Stint API includes fit intercept, matching the React fitted lap-time chart formula.
- `GET /api/analytics/laps/{year}/{round_num}/{driver_number}` returns individual valid laps and associated compound.
- Telemetry API now represents *one selected lap*, with speed, throttle, binary brake, gear and RPM.
- Driver Debrief includes explicit lap selectors (primary and, for 1:1, comparison), alongside one-to-many comparison. Note that race context and estimated distance alignment differ even at the same circuit; time gains are approximate.
- Research Results maintains supplied real-data results; we do not fabricate absent prediction metrics.
- Video module has an end-to-end **synthetic software smoke test** and checkpoint inference. NO real wheel-angle accuracy or F1 generalization has been measured.

**Verification performed in this environment:**
- 38 Python backend/dataset tests passed.
- EfficientNet-B0 + GRU + optical-flow forward pass executed.
- All three neural architecture variants were trained in a minimal, 1-epoch synthetic **smoke test** and checkpoint-based video-to-CSV inference completed.
- 18 TS/TSX files were transpiled for **syntax only**; this is not a type-check or full build.
- Frontend `npm install` timed out; **`npm run build` NOT verified here**.
- No live API end-to-end driver comparison ran here; user must validate the 2024 data paths.
- YOLO segmentation is OPTIONAL and cannot be claimed as trained/tested without a custom wheel mask dataset/checkpoint.

## Mandatory local release gates
1. Create and activate a Python 3.11 environment. `python -m pip install -r backend/requirements.txt` and `python -m pytest -q` from `backend`.
2. `cd frontend`, `npm install`, `npm run build` (must succeed), then `npm run dev`.
3. Start FastAPI with `python -m uvicorn app.main:app --reload --port 8000` from `backend`.
4. Test race schedule; Stint Analysis fitted line; selected-lap Telemetry; Research Results from saved user JSON; Driver Debrief (Bahrain 2024, 1:1 and 1:many); track markers; both PDF and Markdown export. Record screenshots and checked outputs.
5. Check source terms for OpenF1/Jolpica/FastF1 and any video/weights used; keep copyrighted/rights-controlled footage and model artifacts out of the repo.
6. Confirm `git status` excludes secrets, video and large checkpoint files before public push. Run CI and fix any failures.

## Reviewer questions we can answer honestly
- **Why not use measured steering?** Public car telemetry lacks it; video estimation requires domain-specific labels and calibration.
- **Why not claim the best deep-learning model?** There are no measured steering labels evaluated on unseen F1 onboard recordings yet. We provide a disjoint-video benchmark pipeline that will calculate it when data exists.
- **Why not claim validated physical tyre degradation?** Fuel, track evolution, rain, traffic and tyre compound confound lap-time slopes.
- **What is implemented vs planned?** See research and steering module docs; no proprietary F1 team data or team-grade vehicle digital twin is claimed.
