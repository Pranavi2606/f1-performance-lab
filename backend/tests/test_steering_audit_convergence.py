"""Tests for provisional group preview and honest convergence-only training."""
import csv
import json
from pathlib import Path

import pytest
import torch
from torch import nn

from steering_research.split_review import generate
from steering_research.plot_training_history import render
from steering_research import train as tr


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_provisional_split_preview_and_coverage(tmp_path):
    manifest = tmp_path/'steering_data'/'manifest.csv'
    mapping = tmp_path/'steering_data'/'groups.csv'
    records = [dict(video_id=f'vid{i}',frame_index=j,angle_deg=j,frame_path=f'v{i}_{j}.jpg')
               for i in range(6) for j in range(7)]
    groups = [dict(video_id=f'vid{i}',source_recording_group=f'group{i//2}',
                   review_status='UNREVIEWED',evidence_notes='proposed') for i in range(6)]
    _write_csv(manifest,list(records[0]),records)
    _write_csv(mapping,list(groups[0]),groups)
    summary = generate(manifest,mapping,tmp_path/'out',seed=42)
    assert summary['candidate_images']==42
    assert summary['group_crossings']==0
    assert summary['unverified_filename_ids']==6
    assert sum(p['frames'] for p in summary['partition_counts'].values())==42
    assert sum(p['six_frame_sequences'] for p in summary['partition_counts'].values())==12
    assert (tmp_path/'out'/'split_assignments_PREVIEW_ONLY.csv').exists()


def test_provisional_training_requires_explicit_validation_only(tmp_path, monkeypatch):
    rows = [dict(video_id=f'v{i}',frame_index=j,angle_deg=float(j),frame_path='not_used')
            for i in range(3) for j in range(6)]
    monkeypatch.setattr(tr,'read_manifest',lambda _: rows)
    mapping = tmp_path/'review.csv'
    _write_csv(mapping,['video_id','source_recording_group','review_status'],[
        {'video_id':f'v{i}','source_recording_group':f'g{i}','review_status':'UNREVIEWED'}
        for i in range(3)])
    with pytest.raises(ValueError,match='UNREVIEWED'):
        tr.train_evaluate('unused',tmp_path/'out.json',epochs=1,group_map=mapping)
    with pytest.raises(ValueError,match='UNREVIEWED'):
        tr.train_evaluate('unused',tmp_path/'out.json',epochs=1,group_map=mapping,
                          allow_provisional_groups=True)


def test_two_epoch_training_saves_best_and_validation_history(tmp_path,monkeypatch):
    rows=[dict(video_id=f'v{i}',frame_index=j,angle_deg=float(i*15+j),frame_path='not_used')
          for i in range(3) for j in range(6)]
    monkeypatch.setattr(tr,'read_manifest',lambda _:rows)

    class FakeDataset:
        def __init__(self, records, window=6):
            self.samples=[]
            for vid in sorted({r['video_id'] for r in records}):
                seq=[r for r in records if r['video_id']==vid]
                self.samples.append((vid,seq))
        def __len__(self): return len(self.samples)
        def __getitem__(self,i):
            vid,seq=self.samples[i]
            return (torch.zeros((6,3,1,1)),torch.zeros((6,3)),
                    torch.tensor(seq[-1]['angle_deg'],dtype=torch.float32),vid)

    class FakeModel(nn.Module):
        def __init__(self,mode,pretrained=False,freeze_encoder=True):
            super().__init__()
            self.head=nn.Linear(1,1)
        def forward(self,frames,flow=None):
            return self.head(frames.mean((1,2,3,4),keepdim=False).reshape(-1,1)).reshape(-1)

    monkeypatch.setattr(tr,'WheelSequenceDataset',FakeDataset)
    monkeypatch.setattr(tr,'SteeringRegressor',FakeModel)
    mapping=tmp_path/'group_map.csv'
    _write_csv(mapping,['video_id','source_recording_group','review_status'],[
        {'video_id':f'v{i}','source_recording_group':f'g{i}','review_status':'UNREVIEWED'} for i in range(3)])
    output=tmp_path/'experiment.json'
    report=tr.train_evaluate('unused',output,epochs=2,batch_size=1,modes=['cnn'],
                             group_map=mapping,allow_provisional_groups=True,validation_only=True,
                             device_choice='cpu')
    assert report['status']=='exploratory_validation_only'
    assert report['selected_model']['final_test']['status']=='NOT_RUN_PROVISIONAL_SOURCE_GROUPS'
    assert len(report['models']['cnn']['training_history'])==2
    assert all('validation_mae_deg' in epoch for epoch in report['models']['cnn']['training_history'])
    assert (tmp_path/'experiment_cnn.pt').exists()
    history=tmp_path/'experiment_cnn_history.json'
    assert history.exists()
    svg=render(history,tmp_path/'curve.svg').read_text(encoding='utf-8')
    assert 'Validation MAE' in svg
    with pytest.raises(FileExistsError):
        tr.train_evaluate('unused',output,epochs=1,batch_size=1,modes=['cnn'],
                          group_map=mapping,allow_provisional_groups=True,validation_only=True,
                          device_choice='cpu')
