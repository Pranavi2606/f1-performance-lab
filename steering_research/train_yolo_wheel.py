"""Optional YOLOv8-seg fine-tuning on user-labelled steering-wheel masks.
Requires a legitimate Ultralytics-compatible dataset YAML, train/val split and
agreement with Ultralytics licensing. This file never downloads video/labels.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def run(dataset_yaml: str, out_name: str = 'f1_wheel_mask', epochs: int = 30, image_size: int = 640):
    if not Path(dataset_yaml).exists():
        raise FileNotFoundError(f'No dataset yaml: {dataset_yaml}')
    if epochs<1 or image_size<160:raise ValueError('Invalid training settings')
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError('Run pip install ultralytics, and review its AGPL/Enterprise license') from exc
    # Generic YOLOv8n-seg has no pretrained F1 wheel-mask class. This is fine-tuning
    # with user's labelled masks, not zero-shot steering-wheel segmentation.
    model=YOLO('yolov8n-seg.pt')
    train=model.train(data=dataset_yaml,epochs=epochs,imgsz=image_size,name=out_name)
    return train

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--data',required=True,help='Ultralytics instance-segmentation dataset YAML')
    p.add_argument('--name',default='f1_wheel_mask');p.add_argument('--epochs',type=int,default=30)
    p.add_argument('--imgsz',type=int,default=640)
    a=p.parse_args();run(a.data,a.name,a.epochs,a.imgsz)
