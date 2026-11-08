# Experimental steering estimation — isolated research module

This module **does not claim validated accuracy** until you supply rights-cleared, synchronised footage **and measured steering-wheel rotation**. The usual OpenF1 feed has no measured steering angle. A model trained on simulator footage may fail to generalise to F1 onboard cameras.

## Required labelled dataset

Create `manifest.csv` with `video_id,frame_index,frame_path,angle_deg`, for example:

```csv
video_id,frame_index,frame_path,angle_deg
sim_session_1,0,frames/s1_0000.jpg,0.0
sim_session_1,1,frames/s1_0001.jpg,1.8
sim_session_2,0,frames/s2_0000.jpg,-4.0
```

Collect >6 **consecutive** frames per recording, with measured wheel rotation in degrees aligned to video timestamps. Use several independent recordings with varying wheel turns, steering positions, lighting and camera positions. Crop a stable wheel region, consistently across recordings. `angle_deg` must be a physical controller measurement or manually validated reference—not another model's prediction. Negative/positive angles should use a consistent convention.

## Evaluate the architecture

From project root, install optional requirements:

```powershell
python -m pip install -r steering_research/requirements-optional.txt
python -m steering_research.train --manifest steering_data/manifest.csv --output results/steering_ablation.json --epochs 8 --pretrained
```

`--pretrained` downloads ImageNet weights on first run; omit for offline smoke testing (but do not claim competitive performance). Models: **EfficientNet-B0 frame CNN**, **EfficientNet-B0 + causal GRU**, **EfficientNet-B0 + optical-flow statistics + GRU**. The encoder is frozen for a modest compute requirement. Training uses SmoothL1 loss; evaluation uses MAE, RMSE, p95 absolute error, signed bias and per-video errors.

The split is by `video_id`—never random neighbouring frames. Choosing the best architecture using the held-out videos makes those videos a validation set; collect an **independent final test set** for the unbiased final score. Do not report 'best accuracy' until then. Compute p95 error and temporal lag/jitter separately if you have timestamped reference traces; this code does *not* claim those metrics have been evaluated.

## YOLOv8 wheel segmentation: optional

`steering_research.segment.segment_wheel(image, custom_checkpoint)` accepts a **custom-trained wheel segmentation checkpoint**. It is NOT a default automatic steering-wheel detector. To enable YOLO preprocessing you need your own labelled wheel masks, checkpoint and an explicit train/evaluate step. We deliberately do not bundle pretrained generic segmentation weights or pretend ordinary weights know F1 steering wheels. Check [Ultralytics licensing](https://www.ultralytics.com/license), particularly if you publish/deploy code. This step is optional because cropping often provides a simpler, more reproducible baseline.

## No fabricated evidence

No bundled trained checkpoint or F1 steering-error metric. `.pt` weights and video frames are ignored by Git. The original OpenCV image-plane steering prototype remains available under backend/scripts but should not be presented as measured angle or as a validated CNN.

### Capture real ground truth (recommended)

Record two synchronized streams on a simulator: video showing the wheel and steering-controller rotation from the simulator/controller (e.g. `time_s,angle_deg`). For each session:

```powershell
python -m steering_research.prepare_dataset --video my_own_sim_video.mp4 --steering-csv my_own_controller.csv --out-dir steering_data/session_a --video-id session_a --sample-fps 8 --crop 100 120 460 320
```

Set `--offset-s` only after aligning the two clocks with a distinct steering gesture. This captures labelled frames; combine the per-session manifests into one CSV with adjusted paths, keeping recording IDs distinct. Without labels and reliable sync, the steering model cannot produce a credible accuracy result.

### Use the trained model to make a debrief trace

Once you have **trained weights** and a genuinely evaluated model, generate a CSV from permitted video:

```powershell
python -m steering_research.infer --video licensed_onboard.mp4 --checkpoint results/steering_ablation_cnn_gru_flow.pt --output results/estimated_steering.csv --crop 100 120 460 320
```

Use the same crop geometry/preprocessing as training; otherwise domain shift undermines predictions. Optionally pass `--yolo-wheel-checkpoint PATH` **only if you have your own validated wheel-mask model**, and train/evaluate on identically segmented crops; it is not a plug-and-play improvement. Import `estimated_steering.csv` in **Driver Debrief > Experimental Steering**. The CSV uses video seconds, not automatically synchronized F1 telemetry timestamps. `confidence=unvalidated` intentionally avoids inventing confidence scores.

### Train a custom YOLOv8 wheel-segmentation model (only with wheel masks)

Prepare a legitimate Ultralytics **instance segmentation** dataset of wheel polygons with train/val recordings separated by video. Then, after reviewing the Ultralytics license:

```powershell
python -m pip install ultralytics
python -m steering_research.train_yolo_wheel --data steering_data/wheel_mask.yaml --epochs 30
```

Use the resulting verified `best.pt` as `--yolo-wheel-checkpoint` for inference. Retrain CNN/GRU on equivalently masked images before evaluating a YOLO+EfficientNet+GRU pipeline; mixing masked inference with unmasked training is an untested distribution shift. Compare **with vs without masks** on the same held-out recordings. No YOLO wheel weights, metrics, or labelled masks are bundled.
