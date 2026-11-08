# F1 Performance Lab — Vehicle Performance & Decision Intelligence

**Independent engineering portfolio** | Python · FastAPI · React · TypeScript · statistical modelling · machine learning

Research-oriented Formula 1 analysis using publicly available Jolpica classification data and OpenF1 telemetry. Explores vehicle performance, driver-lap comparisons, tyre-stint trends, energy *proxies*, predictive baselines and race strategy scenarios. **Not affiliated with Formula 1, the FIA, or any team.**

## What the application does

| Module | Engineering question / output |
|---|---|
| Race Results | What happened? Published qualifying/grid/finishing positions and status |
| Stint Analysis | How do observed lap times change within a tyre stint? Regression, confidence and cleaning audits |
| Strategy Insights | Which drivers gained or lost positions? Descriptive rather than causal analysis |
| Energy Management | What do published rule constraints imply? Illustrative calculations, not team ERS telemetry |
| Performance Discovery | Speed/acceleration fingerprints, approximate corner-exit comparisons and contextual tyre trends |
| Telemetry Lab | Speed, throttle, binary brake, RPM and gear traces from public data |
| Driver Debrief | Approximate cross-driver lap overlays, track map, braking windows, exportable Markdown/PDF |
| Research Results | Historical race benchmarks and uncertainty-aware model comparisons |
| Steering AI Research | Exploratory onboard-image wheel-rotation CNN/GRU/flow ablation and transparent research limitations |

### Measured research (with limitations)

- **Tyre modelling:** an executed three-race 2024 benchmark (Bahrain, Monaco, Belgium), evaluating 172 observed laps with 47 chronological within-stint test laps across 8 folds. A separate report documents comparisons against simple baselines. These results **do not establish cross-event generalization**.
- **Steering wheel rotation:** an initial one-epoch, randomly initialized frozen-encoder experiment compared image-only CNN, CNN-GRU and CNN-GRU-plus-optical-flow. Recorded validation MAEs were **93.11°, 93.46° and 61.30°** respectively (999 validation sequences). The selected hybrid produced **47.10° MAE on a filename-group-held-out set** (803 sequences). These are **exploratory results only**: the original split had confirmed exact-image train/validation leakage; source-recording independence and mixed footage provenance remain unresolved. The values **must not be used as a clean generalization claim**.
- **Follow-up audit:** of 5,553 images, 6 exact duplicate clusters (12 entries) had contradictory labels; suspected game-rendered images were provisionally quarantined. A resulting **3,690-image candidate** and **40 unverified proposed recording groups** are awaiting source-level validation. Later multi-epoch convergence training is **not included as a completed result**.

A public checkpoint is **not** included. Steering labels represent *manually annotated visible wheel rotation*, **not** steering sensor data. Public telemetry cannot directly diagnose oversteer, yaw/slip, actual tyre wear or proprietary ERS state.

## Run locally

Prerequisites: Python 3.11–3.12, Node.js 22+ (with working npm), network access for public API data.

**Backend** (from `backend/`):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (separate terminal, from `frontend/`):

```powershell
npm install
npm run build
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). API health: `http://localhost:8000/api/health`.

The frontend **requires a running backend** for live race data; publishing a static frontend alone will not deploy the API. Data coverage is determined by the public upstream services and may be incomplete for newer events. This repository deliberately does not include the local F1 image dataset or trained weights.

## Validation

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
```

For the optional steering research dependencies, install separately in a CUDA-capable environment (see [`steering_research/README.md`](steering_research/README.md) and [`REVIEW_AND_CONVERGENCE_START_HERE.md`](REVIEW_AND_CONVERGENCE_START_HERE.md)). This avoids mixing PyTorch requirements into the web API environment.

`GitHub Actions` runs backend/research unit tests and a TypeScript/Vite production build. The package was independently checked with **44 passing local backend tests**; the latest frontend production build must be verified on your machine.

## Methodology, provenance, and responsible use

- [`research/RESEARCH_PROTOCOL.md`](research/RESEARCH_PROTOCOL.md) — modelling questions, evaluation methods and uncertainty.
- [`research/SOURCE_REGISTER.md`](research/SOURCE_REGISTER.md) — source register and data-use caveats.
- [`research/V13_DEBRIEF_UI_REPORT_NOTES.md`](research/V13_DEBRIEF_UI_REPORT_NOTES.md) — comparison display and reporting notes.
- [`steering_research/README.md`](steering_research/README.md) — optional steering architectures, data and training.
- [`PRIVACY_AND_DATA_TERMS.md`](PRIVACY_AND_DATA_TERMS.md) — non-redistribution of third-party video.

**Source links:** [Jolpica](https://github.com/jolpica/jolpica-f1), [OpenF1](https://openf1.org/docs/). This project uses public data and engineering approximations rather than internal team telemetry. It has not been validated as a race-engineering decision support tool.
