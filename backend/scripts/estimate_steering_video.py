"""Experimental *image-derived* steering rotation from user-provided, rights-cleared video.

Usage:
  pip install opencv-python
  python scripts/estimate_steering_video.py --video onboard.mp4 --cx 610 --cy 440 --mx 704 --my 445 --output ../results/steering_cv.csv

The user must provide an approximate wheel CENTER (cx,cy) and a visible MARKER (mx,my)
on the wheel. Lucas-Kanade tracks the marker patch over time. This is image-plane
rotation of a tracked feature about a chosen image center, NOT calibrated steering
sensor angle. Camera motion, parallax, occlusion and marker drift can corrupt it.
"""
import argparse
import csv
import math
from pathlib import Path


def estimate(video: str, cx: float, cy: float, mx: float, my: float, output: str,
             max_seconds: float = 180.0, stride: int = 2):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise SystemExit('OpenCV is optional. Install with: pip install opencv-python') from exc
    if stride < 1 or max_seconds <= 0:
        raise ValueError('stride must be >= 1, max_seconds > 0')
    cap=cv2.VideoCapture(video)
    if not cap.isOpened():
        raise ValueError('Cannot open video. Confirm the path and rights to use the footage.')
    fps=cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:fps=30.0
    ok,first=cap.read()
    if not ok:
        cap.release(); raise ValueError('Unable to read the first frame')
    h,w=first.shape[:2]
    if not all(0<=v<limit for v,limit in ((cx,w),(mx,w),(cy,h),(my,h))):
        cap.release(); raise ValueError('Center/marker point is outside video frame')
    prev=cv2.cvtColor(first,cv2.COLOR_BGR2GRAY)
    point=np.array([[[mx,my]]],dtype=np.float32)
    ref_angle=math.atan2(my-cy,mx-cx)
    prev_angle=ref_angle
    cumulative=0.0
    results=[{'video_elapsed_s':0., 'estimated_rotation_deg':0.,'confidence':'anchor'}]
    frame_no=0
    try:
        while cap.isOpened():
            ok,frame=cap.read()
            if not ok:break
            frame_no+=1
            if frame_no%stride:continue
            if frame_no/fps>max_seconds:break
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            next_point,status,err=cv2.calcOpticalFlowPyrLK(prev,gray,point,None,winSize=(25,25),maxLevel=3,
                              criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,.01))
            if status is None or not status[0][0]:
                results.append({'video_elapsed_s':round(frame_no/fps,3),'estimated_rotation_deg':'','confidence':'tracking_lost'})
                break
            x,y=map(float,next_point[0][0]); uncertainty=float(err[0][0]) if err is not None else float('inf')
            if not (0<=x<w and 0<=y<h):
                results.append({'video_elapsed_s':round(frame_no/fps,3),'estimated_rotation_deg':'','confidence':'out_of_frame'})
                break
            angle=math.atan2(y-cy,x-cx)
            delta=(angle-prev_angle+math.pi)%(2*math.pi)-math.pi
            cumulative+=delta
            results.append({'video_elapsed_s':round(frame_no/fps,3),
                           'estimated_rotation_deg':round(math.degrees(cumulative),3),
                           'confidence':'low' if uncertainty>28 else 'tracking_only'})
            prev,point,prev_angle=gray,next_point,angle
    finally:
        cap.release()
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['video_elapsed_s','estimated_rotation_deg','confidence'])
        writer.writeheader();writer.writerows(results)
    return {'samples':len(results),'file':str(path),'method':'uncalibrated camera-plane feature rotation (LK optical flow)',
            'warning':'NOT official steering angle; NOT degrees of calibrated front wheel or vehicle steering.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',required=True)
    for k in ('cx','cy','mx','my'):
        p.add_argument('--'+k,required=True,type=float)
    p.add_argument('--output',default='../results/steering_cv.csv')
    p.add_argument('--max-seconds',type=float,default=180)
    p.add_argument('--stride',type=int,default=2)
    args=p.parse_args()
    print(estimate(args.video,args.cx,args.cy,args.mx,args.my,args.output,args.max_seconds,args.stride))
