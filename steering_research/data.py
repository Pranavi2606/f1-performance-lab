"""Dataset manifest loader and strict session-level train/test split."""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path
import numpy as np
import cv2
import torch
from torch.utils.data import Dataset

REQUIRED = {'video_id','frame_path','frame_index','angle_deg'}


def read_manifest(path: str | Path) -> list[dict]:
    path = Path(path)
    with path.open(newline='',encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not REQUIRED.issubset(set(reader.fieldnames or [])):
            raise ValueError(f'Manifest requires columns {sorted(REQUIRED)}')
        rows=[]
        for row in reader:
            frame = (path.parent/row['frame_path']).resolve()
            if not frame.is_file(): raise FileNotFoundError(frame)
            rows.append({'video_id':row['video_id'],'frame_path':frame,'frame_index':int(row['frame_index']),
                         'angle_deg':float(row['angle_deg'])})
    if not rows: raise ValueError('Empty labelled manifest')
    if any(not np.isfinite(row['angle_deg']) for row in rows):raise ValueError('Non-finite angle label')
    return rows


def split_sessions(rows: list[dict], seed: int = 42, test_fraction: float = 0.25) -> tuple[list[dict],list[dict]]:
    videos = sorted({r['video_id'] for r in rows})
    if len(videos)<2:raise ValueError('Need at least 2 independent video recordings to split by session')
    rng=np.random.default_rng(seed)
    rng.shuffle(videos)
    n_test=max(1,min(len(videos)-1,round(test_fraction*len(videos))))
    test_ids=set(videos[:n_test]); train_ids=set(videos[n_test:])
    assert not (test_ids & train_ids)
    return [r for r in rows if r['video_id'] in train_ids],[r for r in rows if r['video_id'] in test_ids]


def flow_features(previous: np.ndarray, current: np.ndarray) -> np.ndarray:
    """Mean signed x/y motion and magnitude in wheel crop; image-plane, not angle."""
    a=cv2.cvtColor(previous,cv2.COLOR_RGB2GRAY)
    b=cv2.cvtColor(current,cv2.COLOR_RGB2GRAY)
    flow=cv2.calcOpticalFlowFarneback(a,b,None,0.5,3,15,3,5,1.2,0)
    return np.array([flow[:,:,0].mean(), flow[:,:,1].mean(), np.linalg.norm(flow,axis=2).mean()],dtype=np.float32)


def load_image(path: Path, size: int = 224) -> np.ndarray:
    image=cv2.imread(str(path))
    if image is None:raise ValueError(f'Unreadable image {path}')
    return cv2.cvtColor(cv2.resize(image,(size,size)),cv2.COLOR_BGR2RGB)


class WheelSequenceDataset(Dataset):
    def __init__(self, rows: list[dict], window: int = 6):
        if window<1:raise ValueError('window must be >=1')
        by_video=defaultdict(list)
        for row in rows:by_video[row['video_id']].append(row)
        self.samples=[];self.window=window
        for video, items in by_video.items():
            items=sorted(items,key=lambda r:r['frame_index'])
            for end in range(window-1,len(items)):
                seq=items[end-window+1:end+1]
                # Never bridge missing frame indexes or separate videos.
                if any(b['frame_index']<=a['frame_index'] or b['frame_index']-a['frame_index']>1 for a,b in zip(seq,seq[1:])):continue
                self.samples.append((video,seq))

    def __len__(self): return len(self.samples)

    def __getitem__(self,index):
        video,seq=self.samples[index]
        imgs=[load_image(r['frame_path']) for r in seq]
        frames=[]
        for im in imgs:
            tensor=torch.from_numpy(im.copy()).permute(2,0,1).float()/255.0
            # ImageNet normalization for torchvision pretrained EfficientNet weights.
            mean=torch.tensor([.485,.456,.406]).view(3,1,1)
            std=torch.tensor([.229,.224,.225]).view(3,1,1)
            frames.append((tensor-mean)/std)
        flow=np.zeros((len(imgs),3),dtype=np.float32)
        for t in range(1,len(imgs)):flow[t]=flow_features(imgs[t-1],imgs[t])/10.0
        return torch.stack(frames),torch.from_numpy(flow),torch.tensor(seq[-1]['angle_deg'],dtype=torch.float32),video


def split_train_validation_test(rows: list[dict], seed: int = 42, source_groups: dict[str,str] | None = None) -> tuple[list[dict],list[dict],list[dict]]:
    """Recording-disjoint train/validation/final test. No frame can cross a recording boundary."""
    # By default this remains the original filename-derived split (exploratory only).
    # With source_groups, every clip belonging to one verified underlying recording
    # is assigned to exactly one partition, preventing cross-clip source leakage.
    videos = sorted({source_groups[r['video_id']] if source_groups else r['video_id'] for r in rows})
    if len(videos) < 3:
        raise ValueError('At least three independent recording groups required for train/validation/test')
    rng = np.random.default_rng(seed)
    rng.shuffle(videos)
    n = len(videos)
    n_test = max(1, int(round(n * .20)))
    n_val = max(1, int(round(n * .20)))
    n_test = min(n_test, n-2)
    n_val = min(n_val, n-n_test-1)
    test_ids = set(videos[:n_test])
    validation_ids = set(videos[n_test:n_test+n_val])
    train_ids = set(videos[n_test+n_val:])
    assert train_ids and validation_ids and test_ids
    assert not (train_ids & validation_ids or train_ids & test_ids or validation_ids & test_ids)
    key=lambda r: source_groups[r['video_id']] if source_groups else r['video_id']
    return ( [r for r in rows if key(r) in train_ids],
             [r for r in rows if key(r) in validation_ids],
             [r for r in rows if key(r) in test_ids] )
