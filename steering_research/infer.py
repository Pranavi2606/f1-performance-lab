"""Produce an *experimental* steering CSV from rights-cleared onboard video.
Only works with a trained checkpoint from steering_research.train; no invented angles.
YOLO wheel segmentation is optional and requires an actual custom wheel checkpoint.
"""
from __future__ import annotations
import argparse,csv
from collections import deque
from pathlib import Path
import cv2
import numpy as np
import torch
from .data import flow_features
from .models import SteeringRegressor


def frame_tensor(image):
    resized=cv2.cvtColor(cv2.resize(image,(224,224)),cv2.COLOR_BGR2RGB)
    a=torch.from_numpy(resized.copy()).permute(2,0,1).float()/255.0
    mean=torch.tensor([.485,.456,.406]).view(3,1,1)
    std=torch.tensor([.229,.224,.225]).view(3,1,1)
    return (a-mean)/std,resized


def predict_video(video_path: str, checkpoint: str, output_csv: str, *, crop=None,
                  sample_fps: float = 8.0, yolov8_wheel_checkpoint: str | None = None):
    # Explicitly require trained weights; no untrained network output is presented as an estimate.
    if not Path(checkpoint).is_file():raise FileNotFoundError(f'Trained model checkpoint missing: {checkpoint}')
    bundle=torch.load(checkpoint,map_location='cpu',weights_only=True)
    mode=bundle['mode']
    model=SteeringRegressor(mode,pretrained=False,freeze_encoder=True)
    model.load_state_dict(bundle['weights']);model.eval()
    cap=cv2.VideoCapture(video_path)
    if not cap.isOpened():raise ValueError(f'Could not open permitted video: {video_path}')
    fps=float(cap.get(cv2.CAP_PROP_FPS))
    if fps<=0 or sample_fps<=0:raise ValueError('Invalid video FPS')
    stride=max(1,round(fps/sample_fps))
    count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tensor_frames=deque(maxlen=6); rgb_frames=deque(maxlen=6)
    output=[]
    for frame_idx in range(0,count,stride):
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame_idx)
        ok,frame=cap.read()
        if not ok:continue
        if crop is not None:
            x,y,w,h=crop;frame=frame[y:y+h,x:x+w]
            if frame.size==0:raise ValueError('Crop region outside video frame')
        if yolov8_wheel_checkpoint:
            from .segment import segment_wheel
            frame=segment_wheel(frame,yolov8_wheel_checkpoint)
        tensor,rgb=frame_tensor(frame)
        tensor_frames.append(tensor);rgb_frames.append(rgb)
        if len(tensor_frames)<6:continue
        motion=np.zeros((6,3),dtype=np.float32)
        for j in range(1,6):motion[j]=flow_features(rgb_frames[j-1],rgb_frames[j])/10.0
        with torch.no_grad():
            angle=model(torch.stack(list(tensor_frames))[None],torch.from_numpy(motion)[None] if mode.endswith('_flow') else None)
        output.append({'video_elapsed_s':round(frame_idx/fps,4),
                       'estimated_rotation_deg':round(float(angle.item()),4),
                       'confidence':'unvalidated','model':mode})
    cap.release()
    if not output:raise ValueError('Video too short: need at least six sampled frames')
    out=Path(output_csv);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
    return {'samples':len(output),'output_csv':str(out),'model':mode,
            'measurement_type':'experimental computer-vision estimate; not official steering telemetry',
            'synchronization':'video time only; not automatically aligned with race telemetry'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--video',required=True);p.add_argument('--checkpoint',required=True)
    p.add_argument('--output',required=True);p.add_argument('--sample-fps',type=float,default=8)
    p.add_argument('--crop',nargs=4,type=int);p.add_argument('--yolo-wheel-checkpoint')
    a=p.parse_args()
    print(predict_video(a.video,a.checkpoint,a.output,crop=a.crop,sample_fps=a.sample_fps,yolov8_wheel_checkpoint=a.yolo_wheel_checkpoint))
