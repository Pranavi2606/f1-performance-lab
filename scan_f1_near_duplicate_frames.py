"""Find potentially overlapping frames across filename-derived F1 video IDs.

Evidence tool, NOT a proof of shared source recordings. This script compares
pixel-exact SHA-256 and a 64-bit DCT perceptual hash on full-frame images.

Usage (from F1_Performance_Lab project root):
    python scan_f1_near_duplicate_frames.py \
       --manifest steering_data/f1_steering_manifest.csv \
       --output results/steering_cross_group_similarity.csv

Requires: numpy, opencv-python (already dependencies of the steering module).
"""
from __future__ import annotations
import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

POPCOUNT = np.array([int(i).bit_count() for i in range(256)], dtype=np.uint8)


def resolve_frame(frame_path: str, manifest: Path) -> Path:
    name = Path(frame_path)
    candidates = [name, manifest.parent / name, manifest.parent.parent / name,
                  manifest.parent / name.name, manifest.parent / 'f1_steering_angle_dataset' / 'all_frames' / name.name]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f'Could not locate {frame_path!r}; tried {candidates}')


def phash(image: np.ndarray) -> np.uint64:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thumbnail = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    freqs = cv2.dct(thumbnail)[:8, :8].reshape(-1)
    bitmask = freqs > np.median(freqs[1:])
    value = 0
    for bit in bitmask:
        value = (value << 1) | int(bit)
    return np.uint64(value)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--output',default='results/steering_cross_group_similarity.csv')
    ap.add_argument('--threshold',type=int,default=6,help='64-bit pHash Hamming distance (default: 6)')
    ap.add_argument('--max-examples-per-pair',type=int,default=4)
    args=ap.parse_args()
    if args.threshold<0 or args.threshold>64: ap.error('--threshold must be 0..64')
    manifest=Path(args.manifest)
    with manifest.open(newline='',encoding='utf-8-sig') as f:
        items=list(csv.DictReader(f))
    required={'video_id','frame_path'}
    if not items or not required.issubset(items[0]):
        raise ValueError('Manifest needs video_id and frame_path columns and at least one row')
    raw_hash=[]; percept=[]; paths=[]; videos=[]; angles=[]
    for i,row in enumerate(items,1):
        p=resolve_frame(row['frame_path'],manifest)
        raw=p.read_bytes()
        im=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
        if im is None:raise ValueError(f'Cannot read image: {p}')
        raw_hash.append(hashlib.sha256(raw).hexdigest())
        percept.append(phash(im));paths.append(str(p));videos.append(row['video_id']);angles.append(row.get('angle_deg',''))
        if i%500==0:print(f'Hashed {i}/{len(items)} frames...',flush=True)
    arr=np.asarray(percept,dtype=np.uint64).view(np.uint8).reshape(-1,8)
    vids=np.asarray(videos,dtype=object)
    # Retain the best examples for each *cross-video* pair, not every nearby frame.
    candidates=defaultdict(list)
    for i in range(len(items)):
        if i==0:continue
        different=vids[:i]!=vids[i]
        if not different.any():continue
        xor=np.bitwise_xor(arr[:i],arr[i])
        dist=POPCOUNT[xor].sum(axis=1)
        hits=np.flatnonzero((dist<=args.threshold)&different)
        for j in hits:
            a,b=sorted((videos[j],videos[i]))
            d=int(dist[j]);exact=(raw_hash[j]==raw_hash[i])
            candidates[(a,b)].append((0 if exact else 1,d,j,i,exact))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    records=[]
    for (a,b),entries in sorted(candidates.items()):
        entries.sort()
        for _,d,j,i,exact in entries[:args.max_examples_per_pair]:
            records.append({'video_id_a':a,'video_id_b':b,'pixel_identical_file':str(exact).lower(),
                    'phash_distance':d,'frame_a':paths[j],'frame_b':paths[i],
                    'angle_a_deg':angles[j],'angle_b_deg':angles[i],
                    'interpretation':'exact file duplicate' if exact else 'visual similarity candidate; review manually'})
    cols=['video_id_a','video_id_b','pixel_identical_file','phash_distance','frame_a','frame_b','angle_a_deg','angle_b_deg','interpretation']
    with out.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(records)
    print(f'Scanned {len(items)} frames from {len(set(videos))} filename groups.')
    print(f'Found {len(candidates)} distinct cross-video pairs with >=1 match at pHash distance <= {args.threshold}.')
    print(f'Saved {len(records)} example rows to {out}.')
    print('IMPORTANT: A visual match is a review lead, not proof of shared footage; no matches does not prove independence.')

if __name__=='__main__':main()
