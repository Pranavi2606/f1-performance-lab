import csv
import json
from pathlib import Path
import pytest

from steering_research.import_f1_dataset import (
    parse_recording, get_angle, convert, consecutive_run_lengths,
)
from steering_research.data import split_train_validation_test


def test_recording_names_and_labels():
    assert parse_recording('verstappen-pov-bahrain-left_0032') == ('verstappen-pov-bahrain-left', 32)
    assert parse_recording('albon-monaco_0002.jpg') == ('albon-monaco', 2)
    assert parse_recording('not-sequential') is None
    assert get_angle({'steering_angle':'', 'steering_angle_original':'-189'}) == (-189.0, 'steering_angle_original')
    assert get_angle({'steering_angle':'4', 'steering_angle_original':'5'}) == (4.0, 'steering_angle')
    assert consecutive_run_lengths([1,2,3,5,6,9]) == [3,2,1]


def test_manifest_import_and_audit(tmp_path):
    images=tmp_path/'all_frames';images.mkdir()
    for recording in ('alpha','beta','gamma'):
        for i in range(7):
            (images/f'{recording}_{i:04d}.jpg').write_bytes(b'placeholder')
    csv_path=tmp_path/'dataset_backup.csv'
    with csv_path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['img_name','steering_angle','steering_angle_original'])
        w.writeheader()
        for recording in ('alpha','beta','gamma'):
            for i in range(7):
                w.writerow({'img_name':f'{recording}_{i:04d}','steering_angle':str(i-3),'steering_angle_original':''})
        w.writerow({'img_name':'alpha_0006','steering_angle':'3','steering_angle_original':''})
        w.writerow({'img_name':'alpha_0008','steering_angle':'999','steering_angle_original':''})
    out=tmp_path/'manifest.csv'
    report=convert(csv_path,images,out)
    assert report['images_found']==21
    assert report['recording_groups']==3
    assert report['six_frame_contiguous_sequences']==6
    assert report['excluded']['duplicate_recording_frame']==1
    assert report['excluded']['missing_image']==1
    assert report['training_ready'] is True
    assert report['frame_rate_known'] is False
    assert Path(out.with_suffix('.audit.json')).is_file()
    with out.open(newline='') as f:
        rows=list(csv.DictReader(f))
    train,val,test=split_train_validation_test(rows,seed=42)
    assert {x['video_id'] for x in train}.isdisjoint({x['video_id'] for x in val})
    assert {x['video_id'] for x in train}.isdisjoint({x['video_id'] for x in test})
    assert {x['video_id'] for x in val}.isdisjoint({x['video_id'] for x in test})


def test_out_of_range_explicit_not_clipped(tmp_path):
    d=tmp_path/'frames';d.mkdir()
    (d/'lap_0001.jpg').write_bytes(b'placeholder')
    p=tmp_path/'labels.csv';p.write_text('img_name,steering_angle,steering_angle_original\nlap_0001,,-189\n')
    report=convert(p,d,tmp_path/'manifest.csv')
    assert report['minimum_angle_deg']==-189
    assert report['angles_outside_180_before_optional_exclusion']==1
    filtered=convert(p,d,tmp_path/'filtered.csv',max_angle_abs=180)
    assert filtered['images_found']==0
    assert filtered['excluded']['outside_selected_angle_range']==1
