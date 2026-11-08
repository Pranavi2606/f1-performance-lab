# V13.1 — V13 responsive debrief + V12.1 GPU training

This combined release uses **V13** as its base and adds the **CUDA-aware `steering_research/train.py` from V12.1**. It retains V13's responsive debrief UI and Markdown/PDF exports. `GPU_TRAINING_README.md` is included.

## Files merged
- V13 UI and reports: `frontend/src/components/DebriefPage.tsx`, `frontend/src/components/DebriefExtras.tsx`, `frontend/src/styles.css`, `backend/app/analytics/debrief_artifacts.py`.
- V12.1 GPU support: `steering_research/train.py` (`--device auto|cpu|cuda`, `.to(device)` for model and batches, CPU conversion for evaluation metrics).

## Existing local dataset
The ZIP does **not** contain the complete labelled image dataset (5,553 usable local images). Make sure the paths referenced by `steering_data/f1_steering_manifest.csv` are valid in your extracted project. You can copy your existing local `steering_data` folder into this project or rerun the dataset importer from this new folder.

## Training sanity check (exploratory only)
Activate your working CUDA-enabled environment. From this project's root:

```powershell
python -c "import torch; print(torch.cuda.is_available(),torch.cuda.get_device_name(0))"
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_ablation_gpu.json --epochs 1 --batch-size 2 --device cuda --label-origin manual_f1_annotation
```

The full dataset's filename-based recording groups are **not verified as independent source videos**. Treat all metrics as exploratory until recording-level leakage has been ruled out. The annotated F1 steering angles are **not official sensor readings**.

## Frontend / backend
```powershell
# Terminal 1
cd backend
python -m pytest -q
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
# Terminal 2 (run from project root in another terminal)
cd frontend
npm install
npm run build
npm run dev
```

Then open http://localhost:5173 and validate Driver Debrief at 100% zoom, including PDF and Markdown exports. The frontend production build was **not** run in this packaging environment; backend tests passed 41/41.
