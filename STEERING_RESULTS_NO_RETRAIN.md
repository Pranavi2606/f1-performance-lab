# Steering AI results: no retraining required

This project includes the **actual completed Experiment 01 evaluation** at:

- `results/steering_ablation_gpu.json` (archive and research evidence)
- `frontend/public/steering_ablation_gpu.json` (snapshot displayed in the browser)

Open the frontend and select **Steering AI Research** from the sidebar. Its charts read the saved JSON; neither GPU nor PyTorch is needed to display results. The dashboard also supports importing a new evaluation JSON without retraining.

## Keep your local model files

Copy the three `.pt` checkpoints from your existing V13 `results` folder to the new project's `results` folder *if you plan to resume model research or run inference*. They are not included in this ZIP, because they are generated training artifacts on your PC. **Do not overwrite or delete the originals.** You do not need the checkpoints merely to show these evaluation graphs.

## Running the website

From `frontend`, run `npm install`, `npm run build` and `npm run dev`. The research snapshot page runs independently of the backend, though other race pages still require it. To replace the default displayed snapshot in a future build, copy a validated completed experiment JSON to `frontend/public/steering_ablation_gpu.json` and rebuild the frontend.

## Evidence and limitations

Experiment seed 42, one epoch, no pretrained ImageNet backbone. The source report records 2184 / 999 / 803 train / validation / test sequences and selects CNN-GRU-Flow by validation MAE. The held-out test MAE is 47.1 degrees relative to human-annotated visible wheel rotation. Recording identifiers were derived from filenames and *have not been checked for underlying footage overlap*. No real steering sensor ground truth is available. Use the metrics as exploratory research, not accuracy claims suitable for deployment. Underlying F1 imagery rights remain unverified; the ZIP contains **no dataset frames**.
