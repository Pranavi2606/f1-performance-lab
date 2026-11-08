# CUDA training patch for V12

This is a targeted V12 patch. It does NOT include the later V13 responsive UI improvements. If using V13, copy only `steering_research/train.py` from this package into your V13 directory.

Your RTX 3050 6 GB and PyTorch 2.10.0+cu126 were verified in PowerShell (CUDA True and GPU matrix multiplication).

Run in the project root with your working environment activated:

```powershell
python -m steering_research.train --help
python -m steering_research.train --manifest steering_data/f1_steering_manifest.csv --output results/steering_ablation_gpu.json --epochs 1 --batch-size 2 --device cuda --label-origin manual_f1_annotation
```

The above one-epoch test is **exploratory** and does not establish valid final accuracy. For a scientifically defensible evaluation, first verify that inferred `video_id` groups correspond to independent recordings, check cross-group duplicates and review ambiguous labels. Until then, any accuracy is preliminary and may be contaminated by group leakage.

For follow-up experiments, use `--pretrained` after internet access for ImageNet backbone weights is confirmed. Use batch size 2 initially. If CUDA runs out of memory, reduce to 1. The code freezes EfficientNet-B0's backbone and trains only GRU/head; for full fine-tuning, additional code is needed. Pretrained weights are especially important for this small data regime.

**No fabricated results:** this package contains no new F1 model accuracy report or pretrained checkpoints.
