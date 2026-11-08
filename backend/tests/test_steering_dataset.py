from pathlib import Path
import numpy as np
import cv2
import pytest
pytest.importorskip("torch")
pytest.importorskip("torchvision")
pytest.importorskip("cv2")
from steering_research.data import split_sessions, flow_features, WheelSequenceDataset
from steering_research.train import metrics


def test_video_disjoint_and_metrics():
    rows=[{'video_id':f'v{i}','frame_path':Path('x.jpg'),'frame_index':j,'angle_deg':float(j)} for i in range(4) for j in range(6)]
    train,test=split_sessions(rows,seed=15)
    assert {r['video_id'] for r in train}.isdisjoint({r['video_id'] for r in test})
    assert metrics([0,5],[1,2])['mae_deg']==2.0
    assert metrics([],[])['status']=='unavailable'


def test_flow_and_consecutive_windows(tmp_path):
    rows=[]
    for i in range(7):
        img=np.zeros((32,32,3),dtype=np.uint8)
        cv2.circle(img,(10+i,16),3,(255,255,255),-1)
        path=tmp_path/f'{i}.jpg';cv2.imwrite(str(path),img)
        rows.append({'video_id':'v','frame_path':path,'frame_index':i,'angle_deg':i*1.0})
    ds=WheelSequenceDataset(rows,window=6)
    assert len(ds)==2
    f,flow,angle,video=ds[0]
    assert f.shape==(6,3,224,224)
    assert flow.shape==(6,3)
    assert video=='v'
    assert angle.item()==5.0
