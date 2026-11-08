# F1 Performance Lab V13.3 — Unified Release

This archive merges BOTH V13.2 variants:

- **No-Retrain**: dedicated `Steering AI Research` sidebar tab, responsive model comparison charts, original measured evaluation JSON bundled in both `frontend/public/steering_ablation_gpu.json` and `results/steering_ablation_gpu.json`, JSON import/export. **Opening the results page does not train any model.**
- **Audit/Training**: `Research Results` steering panel, CUDA-aware `steering_research/train.py`, optional single-model runs / multiple epochs / checkpoint warm-start / training-history files, `audit_recording_groups.py`, mapped recording-group splits via `data.py`, `plot_training_history.py`, and `research/SOURCE_REGISTER.md` provenance notes.
- **V13**: responsive Driver Debrief, real-data overlays, PDF and Markdown report generators and the original race analysis pages.
- Strategy Insights uses `Largest Position Gain / Largest Position Loss`, not personalizing language.

## Use the portal without training

1. Extract this archive into a **new** folder, not on top of V13/V13.1.
2. In `frontend`: `npm install`, `npm run build`, then `npm run dev` or `npm run preview` after building.
3. Open **Steering AI Research** in the sidebar; V13.3 bundles the real saved one-epoch evaluation.
4. **Research Results** also has a steering experiment panel. Its import works with a local JSON; to auto-load there, place the same JSON at `frontend/public/research/steering_ablation_gpu.json`.
5. For the remaining race tabs, run the backend separately from `backend`: `python -m uvicorn app.main:app --reload --port 8000`.

## Preserve your trained models

The user-generated `.pt` model checkpoints, steering dataset frames, and local Python virtual environment are NOT part of this ZIP. **Do not delete the older project directory or checkpoints.** For future warm-starting, copy the three `results/steering_ablation_gpu_*.pt` files from your V13 folder to this project's `results/`. This is **not needed merely to show charts**. Never overwrite the bundled original JSON with later experimental results; write new output filenames.

## Audit recording independence before new generalization claims

From the project root, with existing `steering_data` imported:

```powershell
python -m steering_research.audit_recording_groups --manifest steering_data/f1_steering_manifest.csv
```

Review `steering_data/recording_groups_review.csv` and group source clips and edits that share underlying footage; record evidence and set VERIFIED only when justified. Then:

```powershell
python -m steering_research.audit_recording_groups --manifest steering_data/f1_steering_manifest.csv --check
```

There are no verified session keys / driver numbers in the original manifest. Do not invent them. A filename-disjoint split is exploratory, not proof of independent source footage.

## Optional longer training (requires your dataset and compatible CUDA PyTorch)

After completing the group audit, a small new pretrained convergence experiment can be run with a new output prefix:

```powershell
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_convergence_pretrained.json --modes cnn_gru_flow --epochs 12 --batch-size 2 --device cuda --pretrained --max-train-sequences 500 --max-validation-sequences 250 --group-map steering_data/recording_groups_review.csv
```

Generate a **training-loss-only** plot after that run:

```powershell
python -m steering_research.plot_training_history --history results/steering_convergence_pretrained_cnn_gru_flow_history.json --output results/steering_convergence_loss.svg
```

A warm-start with the old checkpoint is possible only on the old filename-derived split and is not an exact continuation (optimizer state missing), so it must not be presented as a clean audited evaluation. See `V13_2_RESEARCH_START_HERE.md` and `STEERING_RESULTS_NO_RETRAIN.md` for details.

## Evidence and verification

The bundled evaluation snapshot is the actual user's Experiment 01: 1 epoch, unpretrained backbone; validation MAEs of 93.1129° (CNN), 93.4638° (CNN-GRU), and 61.2973° (CNN-GRU-Flow). Selected model test MAE 47.1° over 803 overlapping six-frame sequences. **This is exploratory** pending recording leakage auditing. The results are referenced to human-annotated visual wheel rotation, not official steering telemetry. No underlying F1 footage or dataset images are redistributed.

Automated validation and build details should be recorded separately from the archive; passing compilation/tests does not substitute for checking browser downloads and live API data.
