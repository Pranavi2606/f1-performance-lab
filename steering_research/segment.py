"""Optional YOLO-based *wheel-specific* mask preprocessing (requires trained checkpoint).
Generic COCO/YOLO pretrained weights do not include an F1 steering-wheel mask.
"""
from pathlib import Path
import cv2
import numpy as np


def segment_wheel(image_bgr: np.ndarray, checkpoint: str) -> np.ndarray:
    if not Path(checkpoint).is_file():raise FileNotFoundError('Wheel-specific segmentation checkpoint does not exist')
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError('Install optional ultralytics package and review its AGPL/commercial terms') from exc
    result=YOLO(checkpoint).predict(image_bgr,verbose=False)[0]
    if result.masks is None or not len(result.masks.data):
        raise ValueError('Custom wheel segmentation did not produce a mask')
    masks=result.masks.data.detach().cpu().numpy()
    areas=masks.reshape(len(masks),-1).sum(axis=1)
    mask=cv2.resize(masks[int(np.argmax(areas))].astype(np.float32),(image_bgr.shape[1],image_bgr.shape[0]))>0.5
    return (image_bgr*mask[:,:,None]).astype(np.uint8)
