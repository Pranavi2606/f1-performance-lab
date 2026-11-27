# Deploy F1 Performance Lab on Vercel (two projects)

The application is a Vite/React frontend plus a FastAPI backend. **Do not deploy just the frontend**: race-data pages and saved research benchmarks require the Python API. Vercel's multi-service feature has a separate access/availability path; **two regular Vercel projects from the same GitHub repository** are the straightforward configuration.

## 1. Backend project — FastAPI

1. In [Vercel New Project](https://vercel.com/new), import `Pranavi2606/f1-performance-lab`.
2. Set project **Root Directory** to `backend`.
3. Select/detect **FastAPI** (Python runtime). Leave Node/Vite build commands and Uvicorn start commands **unset**: Vercel automatically runs the `backend/index.py` FastAPI entrypoint as a function.
4. Deploy the branch containing these fixes (preview first, then main after merging). Check `https://YOUR-BACKEND.vercel.app/api/health` and `/api/benchmark/latest`.
5. Once you know the frontend URL, set the backend project's environment variable:

   `CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app`

   Add other trusted preview origins separated by commas only if needed, and **redeploy** after changing environment settings. Never use `*` with credentialed endpoints.

The `backend/data/cross_event_real.json` file is a copy of the actual executed historical research result, bundled because backend-root deployments do not include root `results/`. When new benchmark results are independently verified, update both the root report and this deployable snapshot.

## 2. Frontend project — Vite / React

1. Create a **second** Vercel project from the **same repository**. Choose a different project name.
2. Set **Root Directory** to `frontend`; Framework Preset: **Vite**. Build: `npm run build`; Output Directory: `dist`.
3. Set the frontend project's environment variable **before deploying**:

   `VITE_API_BASE_URL=https://YOUR-BACKEND.vercel.app/api`

   Include the `/api` suffix; omit the trailing slash. This is an intentionally public build-time URL, **not a secret**.
4. Deploy, copy the resulting `https://YOUR-FRONTEND.vercel.app` URL, then update the backend `CORS_ORIGINS` from step 1 and redeploy backend.
5. If the frontend domain or backend URL changes, **redeploy** the affected project so new build-time settings apply.

Local development remains unchanged: `frontend/vite.config.ts` proxies `/api` to `http://127.0.0.1:8000` whenever `VITE_API_BASE_URL` is unset.

## 3. Live smoke tests (do not skip)

- Backend: `/api/health` returns status `ok`; `/docs` renders; `/api/benchmark/latest` returns actual OpenF1 2024 report.
- Frontend from an incognito browser: top bar says **API CONNECTED**; Research Results shows three races and 47 within-stint test laps; Steering AI Research shows labelled exploratory plots from the bundled JSON.
- Race Results: select 2024 Bahrain and verify actual API data are visible. Check Console and Network for 403/404/502 errors.
- Stint Analysis, Telemetry, Driver Debrief and Markdown/PDF exports: run with at least one completed event where OpenF1 coverage exists. Report missing data explicitly, never fabricate it.
- Test an unavailable/upcoming race: the API should report missing session rather than silently selecting a different race.
- Check desktop and mobile. Confirm that the frontend can call the backend from its deployed origin (CORS).

## Caveats and safe publishing

- Vercel Functions have bundle-size, memory and execution-time limits. Long requests that fetch many OpenF1 car/location samples may still fail under provider timeouts; consider a persistent backend or cached snapshots if needed.
- The historical result is a **within-stint** chronology benchmark, **not** cross-circuit generalization. Steering training results are **not** a source-independent accuracy claim.
- **Never deploy private training datasets or third-party F1 onboard frames without redistribution rights.** No CUDA or GPU model server is included in this deployment.
- Public OpenF1/Jolpica endpoints have rate/availability constraints. A green unit-test run does not guarantee availability of live historical requests.
