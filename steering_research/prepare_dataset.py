"""Pair permitted video frames with timestamped physical steering-controller measurements.
Sensor CSV: time_s,angle_deg. Video and controller start offset must be known.
"""
from __future__ import annotations
import argparse,csv
from pathlib import Path
import cv2
import numpy as np


def prepare(video, steering_csv, out_dir, video_id, offset_s=0.0, sample_fps=8.0,
            crop=None, max_gap_s=0.12):
    out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
    with open(steering_csv,newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    if not rows or not {'time_s','angle_deg'}.issubset(rows[0]):
        raise ValueError('Sensor CSV requires time_s,angle_deg')
    sensor=sorted((float(r['time_s']),float(r['angle_deg'])) for r in rows)
    times=np.array([r[0] for r in sensor]);angles=np.array([r[1] for r in sensor])
    if len(times)<2 or np.any(np.diff(times)<=0):raise ValueError('Need increasing controller timestamps')
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise ValueError(f'Cannot open video: {video}')
    fps=float(cap.get(cv2.CAP_PROP_FPS))
    if fps<=0 or sample_fps<=0:raise ValueError('Invalid video FPS')
    length=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stride=max(1,round(fps/sample_fps));results=[]
    frames_dir=out_dir/'frames';frames_dir.mkdir(exist_ok=True)
    for frame_id in range(0,length,stride):
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame_id)
        ok,frame=cap.read()
        if not ok:continue
        video_sec=frame_id/fps
        sensor_sec=video_sec+offset_s
        nearest=int(np.argmin(np.abs(times-sensor_sec)))
        if sensor_sec<times[0] or sensor_sec>times[-1] or abs(times[nearest]-sensor_sec)>max_gap_s:continue
        if crop:
            x,y,w,h=crop
            frame=frame[y:y+h,x:x+w]
            if frame.size==0:raise ValueError('Crop outside frame')
        name=f'{video_id}_{len(results):06d}.jpg'
        cv2.imwrite(str(frames_dir/name),frame)
        results.append({'video_id':video_id,'frame_index':len(results),'frame_path':f'frames/{name}',
                        'angle_deg':round(float(np.interp(sensor_sec,times,angles)),5)})
    cap.release()
    manifest=out_dir/f'manifest_{video_id}.csv'
    with manifest.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['video_id','frame_index','frame_path','angle_deg'])
        writer.writeheader();writer.writerows(results)
    return {'manifest':str(manifest),'frames':len(results),'video_id':video_id,
            'note':'Labels interpolated from real supplied controller readings; synchronization offset must be established independently.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--steering-csv',required=True)
    p.add_argument('--out-dir',required=True);p.add_argument('--video-id',required=True)
    p.add_argument('--offset-s',type=float,default=0);p.add_argument('--sample-fps',type=float,default=8)
    p.add_argument('--crop',type=int,nargs=4,metavar=('X','Y','W','H'))
    a=p.parse_args();print(prepare(a.video,a.steering_csv,a.out_dir,a.video_id,a.offset_s,a.sample_fps,a.crop))
