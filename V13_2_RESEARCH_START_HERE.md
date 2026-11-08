# V13.2 — UI results + recording audit + longer training

This update keeps V13.1 UI/export work and CUDA training. Full source images, the steering manifest, and your prior checkpoints are NOT included; preserve them on your PC.

## Show the EXISTING one-epoch results without training

- Keep `results/steering_ablation_gpu.json` and the `.pt` checkpoints safe.
- Option A: open the portal > Research Results > Steering AI Research > Import Steering Results JSON, choose existing `results/steering_ablation_gpu.json`.
- Option B: for a persistent published chart, copy `results/steering_ablation_gpu.json` to `frontend/public/research/steering_ablation_gpu.json` and rebuild. Check whether the report or any source names should be shared publicly.
- This dashboard reports saved validation and final-test results with explicit limitations.

## Audit the true source groups BEFORE trustworthy new benchmarking

```powershell
python -m steering_research.audit_recording_groups --manifest steering_data/f1_steering_manifest.csv
```

Fill `steering_data/recording_groups_review.csv`. Every `video_id` needs an evidence-based `source_recording_group` and `review_status=VERIFIED`. Related camera edits and video variants MUST share a group. Exact session keys/driver numbers are unavailable in the existing manifest and must not be guessed. Verify:

```powershell
python -m steering_research.audit_recording_groups --manifest steering_data/f1_steering_manifest.csv --check
```

## Small convergence run (NOT final evaluation)

One model first. A random, frozen encoder is a poor learning baseline; use pretrained weights, subject to download availability. Note: the training script's `--epochs` means full passes through selected training sequences; `--max-train-sequences 500` means 500 overlapping six-frame windows, NOT 500 distinct source clips.

```powershell
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_convergence_pretrained.json --modes cnn_gru_flow --epochs 12 --batch-size 2 --device cuda --pretrained --max-train-sequences 500 --max-validation-sequences 250 --group-map steering_data/recording_groups_review.csv
```

Train loss (SmoothL1) is written after each epoch to `results/steering_convergence_pretrained_cnn_gru_flow_history.json`. Validation MAE is reported after the run. You cannot accurately claim an eighth-epoch plateau unless the measured curve shows it; training-loss stability also does not prove generalization. **Do not use its test MAE for model selection**.

## Warm-start from EXISTING one-epoch checkpoint (optional, less scientifically useful)

The following reuses the prior architecture weights, but the Adam optimizer state was not saved. This is NOT an exact continuation; and it retains the same randomly initialized, frozen encoder. It cannot be used with the newly audited split.

```powershell
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_warmstart_exploratory.json --modes cnn_gru_flow --resume-from results/steering_ablation_gpu.json --epochs 10 --batch-size 2 --device cuda --seed 42
```

This will evaluate the historical filename split again. Treat it as exploratory, never replace the original results or report it as leak-free.

## Full benchmark with audited split (separate run)

Only after the recording audit, train all three models on the same verified partitions using `--group-map`, `--pretrained`, and a separate output filename. Record seed, epoch count, learning rate and measured curves. Do not repeatedly use the final test to tune architectures.

## Frontend verification

From `frontend`: `npm install`, `npm run build`, `npm run preview`. Check Research Results, imported report and other tabs at 100% browser zoom. A production frontend build is not verified in this tool environment until your computer confirms it.

## Render the measured loss curve for the portfolio

After your convergence run:

```powershell
python -m steering_research.plot_training_history --history results/steering_convergence_pretrained_cnn_gru_flow_history.json --output results/steering_convergence_loss.svg
```

The SVG can be committed to GitHub and linked in your research page. Its caption must say *training loss only* until you implement per-epoch validation and verify stabilization on unseen groups.
