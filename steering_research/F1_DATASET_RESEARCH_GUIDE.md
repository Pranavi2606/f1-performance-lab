# F1 steering annotation study — reproducible, no fabricated metrics

**Release status:** dataset importer and split-safe ablation implemented; **no real-data training completed in this execution environment** (the Hugging Face host could be inspected on the web, but dataset downloads failed in the container due to DNS). Do not describe this as a trained F1 steering estimator or claim accuracy numbers until the report below exists and shows real held-out results.

## Verified source and label semantics

- Dataset: https://huggingface.co/datasets/daniel-saed/F1-steering-angle-dataset
- Published as ~6,890 onboard image frames (~2.89 GB), `all_frames/*.jpg` plus `dataset_backup.csv`.
- CSV columns include `img_name`, `steering_angle`, `steering_angle_original`, `team`, `driver`, `track`, etc. Many metadata fields are blank; angle values can lie outside ±180 degrees. Dataset README is effectively empty.
- Labels are annotations of wheel rotation, **not direct FIA/team steering sensor readings**.
- The numbered images may form short consecutive sequences but their frame rate, continuity, source recording boundaries and consistent camera transformations are **not established**. The filename-prefix rule groups candidate sequences only; review the grouping audit manually before claiming temporal-model performance.
- Dataset page states MIT, but that does not establish redistribution rights for the underlying F1 video frames. Do not commit the images or redistribute sample images/videos in this repo until permissions are verified.

## Download and audit

Run from project root (with enough free space, optionally in a new Python venv):

```powershell
python -m pip install huggingface_hub
python -m steering_research.import_f1_dataset --download --dataset-root steering_data/f1_steering_angle_dataset --manifest steering_data/f1_steering_manifest.csv
```

This downloads the actual source repository using Hugging Face's supported client. The script does **not** bundle training images or invented results. Inspect:

```
steering_data/f1_steering_manifest.csv
steering_data/f1_steering_manifest.audit.json
```

The audit reports number of usable images, recording groups, consecutive six-frame sequences, missing images, duplicate frame indexes, label sources, non-±180° annotations and missing/invalid labels. Source images are ignored by `.gitignore`.

If files already exist locally, omit `--download` and point `--dataset-root` at the directory containing `dataset_backup.csv` and `all_frames/`.

**Before training:** visually confirm candidate prefix groups correspond to independent recordings, confirm chronological suffix increments, verify a consistent crop and angle convention, check annotated errors/outliers, and confirm the images represent the view used in inference. If not, rebuild a corrected manifest with validated `video_id`s. A guessed filename group is insufficient proof of independent held-out videos.

## Three-model comparison (real data)

```powershell
python -m pip install -r steering_research/requirements-optional.txt
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_ablation.json --epochs 8 --batch-size 4 --pretrained --label-origin manual_f1_annotation
```

Three ablations:
1. EfficientNet-B0 CNN on final image.
2. EfficientNet-B0 features + forward GRU over six frames.
3. EfficientNet-B0 + optical-flow summary + forward GRU over six frames.

All use the *same* recording-disjoint train/validation/test split (seed 42). Validation MAE selects the best model. **Final test MAE/RMSE/p95/bias is computed only once for the selected winner**, from previously unseen recordings. Do not repeatedly optimize after looking at final test errors. Video-ID leakage due to improper original grouping remains a risk until verified. These metrics are relative to the manual annotations, not sensor truth. For a more reliable conclusion, rerun with multiple truly independent recording splits, reporting variability without reusing the final test to tune the model.

Computational caveat: this repository freezes the CNN encoder for fast, reproducible prototyping. The models may underfit; strong performance is **not guaranteed**. ImageNet weights require online download when using `--pretrained`. GPU is helpful. **Do not claim best-in-class results merely from comparing these three baselines.**

## Integrate with Driver Debrief

Only use a selected checkpoint with the same preprocessing/crop and rights-cleared F1 onboard video, then run:

```powershell
python -m steering_research.infer --video your_licensed_onboard.mp4 --checkpoint results/steering_ablation_cnn_gru_flow.pt --output results/estimated_steering.csv
```

Replace the checkpoint path with the actual selected model path from the report. Import the CSV under **Driver Debrief > Experimental Steering**. The video output is still a model **estimate** and is **not synchronized** to OpenF1 telemetry without validated time alignment. It cannot prove oversteer or understeer.

## Report claims you may / may not make

- **Currently supported:** "Implemented an auditable importer and recording-disjoint validation framework for F1 onboard steering-angle annotations, with CNN, temporal GRU, and optical-flow fusion ablations."
- **After training:** "Evaluated steering-angle estimates against manually annotated F1 onboard frames with [measured error] on [specified independent recordings]."
- **Not supported:** "Obtained official F1 steering telemetry," "achieved 3° accuracy" or "detected oversteer" without independent supporting evidence.
