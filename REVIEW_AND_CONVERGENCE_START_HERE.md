# Steering CV source review + convergence study (V13.3, consolidated)

**Nothing in this update deletes images, rewrites manual steering labels, retrains old models, or modifies the saved one-epoch results.** This is an additive continuation of V13.3, not a newly invented experiment outcome.

## What is actually known

- The original dataset contained **5,553 labelled image entries**, 72 filename-derived groups.
- Six SHA-256 duplicate-image clusters (12 entries) crossed the original train/validation split and had inconsistent labels.
- The **3,690-entry candidate manifest** quarantined all 12 conflicting entries and provisionally set aside 1,851 `juego` entries believed to be game-rendered.
- The candidate set has 66 filename-derived IDs and **40 proposed** driver/event source groups. They remain `UNREVIEWED`.
- Provisional split preview, seed=42, based on those proposed groups: TRAIN 2,432 frames / 1,548 sequences, VALIDATION 431 / 284, TEST RESERVED 827 / 501. There are **zero group crossings in the splitting algorithm**.
- An earlier *capped* perceptual-hash CSV produces 48 cross-partition example matches across 21 group-pairs; these are review leads, NOT confirmed source-video duplicates. Zero *confirmed byte-identical* cross-group pairs were observed in the completed exact-hash audit, but the source-video independence audit is incomplete.

## Keep your old outputs safe

Preserve the full `steering_data/` directory, the original `results/steering_ablation_gpu.json`, all three `steering_ablation_gpu_*.pt` checkpoints, and your original manifests. The new script refuses to reuse their F1-trained checkpoints with a changed source group split. Do **not** publish source images or the locally generated review gallery without footage rights.

## Run from the consolidated project's root (containing `frontend` and `steering_research`)

Your existing candidate manifest and recording map must remain together in `steering_data` (where your importer created them). **If they live in your older V13.1 directory, supply their absolute paths instead of duplicating 3 GB of images.** If needed, use PowerShell variables: `$old='C:\path\to\F1_Performance_Lab_v13.1'` and specify `"$old\steering_data\..."`.

### 1. Reproduce the non-certifying split preview

```powershell
python -m steering_research.split_review `
  --manifest steering_data/f1_steering_candidate_real_review.csv `
  --group-map steering_data/recording_groups_candidate_UNREVIEWED.csv `
  --similarity-csv results/steering_cross_group_similarity.csv `
  --output-dir results/steering_split_review
```

Outputs:

- `split_summary_PREVIEW_ONLY.json` — counts, provisional status, and warnings;
- `split_assignments_PREVIEW_ONLY.csv` — 66 filename groups and their partitions;
- `cross_split_visual_REVIEW.csv` — suspected cross-partition pHash matches requiring manual review.

The report is based on source groups, not fabricated OpenF1 Session Keys. It does NOT mark the 40 proposals VERIFIED.

### 2. Review the visual candidates locally

```powershell
python -m steering_research.build_review_gallery `
  --review-csv results/steering_split_review/cross_split_visual_REVIEW.csv `
  --output results/steering_split_review/cross_split_gallery_LOCAL_ONLY.html
```

Open the generated HTML **on your own PC**. If source image paths are still valid, it embeds reduced images side by side. If images are missing, inspect the paths in the report from the original dataset location. A pHash distance near zero is NOT conclusive when the cockpit fills most of the view. Compare the source video, frame sequence, camera overlay and timeline. For each suspicious pair, manually record SAME_SOURCE, DIFFERENT_SOURCE, or UNCERTAIN in `cross_split_visual_REVIEW.csv` with supporting evidence. Merge groups when a shared source is confirmed or uncertain enough that keeping them apart would be unsafe. Re-run Step 1 after updating the mapping. **Do not change `review_status` to VERIFIED merely to bypass the training guard.**

### 3. Exploratory *validation-only* 12-epoch convergence experiment

This is allowed while the source review is incomplete, provided the experiment is labelled exploratory and produces **no final-test score**. Source-group uncertainty can still affect validation MAE. A genuine final benchmark needs an independently reviewed source split.

```powershell
python -m steering_research.train `
  --manifest steering_data/f1_steering_candidate_real_review.csv `
  --group-map steering_data/recording_groups_candidate_UNREVIEWED.csv `
  --allow-provisional-groups --validation-only `
  --output results/steering_convergence12_PROVISIONAL.json `
  --modes cnn_gru_flow --pretrained --epochs 12 `
  --max-train-sequences 500 --max-validation-sequences 200 `
  --batch-size 2 --device cuda --amp --lr 0.001 `
  --early-stopping-patience 4
```

- Train from generic pretrained **ImageNet** backbone, NOT your potentially leaked F1 checkpoints.
- EfficientNet feature encoder remains frozen for this fast convergence study. The GRU/head train; a later experiment can explore backbone fine-tuning.
- `--pretrained` may download torchvision's ImageNet weights once; internet is needed for the first download.
- After every epoch, writes `results/steering_convergence12_PROVISIONAL_cnn_gru_flow_history.json` and saves the **best-so-far validation checkpoint**. Early stopping may end before 12 epochs.
- New report includes the training-median constant-angle baseline, validation metrics and **no final-test result**. Model complexity is not independently demonstrated from this single-model run.
- If this run is too slow on the RTX 3050, first use a NEW output name and 150 training / 80 validation sequences with `--epochs 3` to verify throughput. Do not run two jobs concurrently.

### 4. Export measured curves and show them in the portal

```powershell
python -m steering_research.plot_training_history `
  --history results/steering_convergence12_PROVISIONAL_cnn_gru_flow_history.json `
  --output results/steering_convergence12_PROVISIONAL.svg
```

The SVG contains separate axes for **training SmoothL1 loss** and **validation MAE in degrees**. Do not state the model stabilised after 8 epochs unless the measured curve actually supports that claim.

Run the portal (`npm install; npm run build; npm run dev` in `frontend`). In **Steering AI Research**, use **Import newer results JSON** and select `results/steering_convergence12_PROVISIONAL.json`; the page now plots your per-epoch curves and says that final testing was deliberately skipped. The original Experiment 01 remains bundled as the default report.

### 5. Future final evaluation (not yet cleared)

After independently verifying source videos and removing/re-grouping temporal overlaps, freeze a new group map and create a fresh benchmark run. Do not reuse old F1-trained weights, and do not reuse exploratory validation results as independent generalisation claims.

## Verification performed here

- 3 newly added tests + 41 prior backend tests = **44 tests passed**.
- Data-free preview exercised against the supplied original 5,553-row manifest, exact-hash conflicts, and 66-ID proposed mapping; expected candidate totals reproduced.
- One- and two-epoch trainer behaviour tested with a lightweight mocked model (including validation-history saving, checkpoint protection, and no final test in provisional mode).
- Gallery generator checked on local example images, and Python modules compiled.
- Full native CUDA training and the new frontend production build still need verification on your Windows machine.
