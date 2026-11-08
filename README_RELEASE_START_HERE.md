# F1 Performance & Strategy Lab — start here

This repository is a **public-data research prototype**, not an F1-team engineering tool. It combines:

- **Race results** and session schedule (Jolpica)
- **Stint analysis**, context-aware tyre regression and research models (OpenF1)
- **Research Results dashboard** featuring the executed 2024 three-event benchmark (47 within-stint held-out laps)
- **Lap telemetry**: selected-driver/selected-lap speed, throttle, binary brake, gear, RPM
- **Driver Debrief**: 1:1 and 1:many fastest/selected-lap overlays, time-delta proxy, inferred braking zones, track map, exportable PDF and Markdown
- **Optional steering CV research**: CNN (EfficientNet-B0), CNN+GRU, CNN+optical-flow+GRU, with custom YOLO wheel-mask preprocessing as an optional *untrained* integration hook. This is NOT an accurate steering estimator until independently evaluated on ground-truth labels.

## Local setup on Windows PowerShell

```powershell
# From repo root
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
cd backend
python -m pytest -q
python -m uvicorn app.main:app --reload --port 8000
```

In a **second PowerShell terminal**:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Open http://127.0.0.1:5173 and try 2024 Bahrain. If seasons do not load, open http://127.0.0.1:8000/api/health and /api/seasons/2024/races. Node 22 LTS is a sensible choice. The frontend build must succeed on your machine; this build was not independently verified in the generation environment.

## Research reproduction

```powershell
cd backend
python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json
python scripts/generate_engineering_brief.py --input ../results/cross_event_real.json --output ../results/ENGINEERING_BRIEF_LIVE.md
```

See `research/V11_RELEASE_CANDIDATE.md`, `research/RESEARCH_PROTOCOL.md` and `steering_research/README.md` for methodology and limitations. The correct language for the findings is **within-stint lap-time prediction on historical public observations**, not an accurate F1 vehicle digital twin or calibrated steering diagnosis.


## V12 — F1 labelled steering frame dataset adapter

V12 adds `steering_research/import_f1_dataset.py` and `steering_research/F1_DATASET_RESEARCH_GUIDE.md` to connect the publicly documented F1 steering annotations to the three architecture ablations. It audits missing images, out-of-range manual labels, inferred recording groups and consecutive-frame coverage before training. The training script now performs recording-disjoint train/validation/final-test splits and uses validation alone to choose the model. **No real F1 steering training or accuracy claim is included.** The actual dataset is not bundled; download locally using the instructions in the guide.
