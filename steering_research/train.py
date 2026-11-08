"""Steering-ablation training with per-epoch validation and honest split labels.

A provisional group map is permitted ONLY for explicitly exploratory, validation-only
convergence runs. It never produces a held-out *final test* claim. Prior F1-trained
weights must not be reused after changing partitions.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from .data import WheelSequenceDataset, read_manifest, split_train_validation_test
from .models import SteeringRegressor

MODES = ('cnn', 'cnn_gru', 'cnn_gru_flow')


def metrics(truth, estimates):
    a = np.asarray(truth, dtype=float)
    b = np.asarray(estimates, dtype=float)
    if not len(a):
        return {'status': 'unavailable', 'reason': 'No labelled examples'}
    if len(a) != len(b):
        raise ValueError('Ground truth and estimate lengths differ')
    error = b-a
    return {
        'status': 'computed', 'n': len(a),
        'mae_deg': round(float(np.mean(np.abs(error))), 4),
        'rmse_deg': round(float(np.sqrt(np.mean(error**2))), 4),
        'p95_abs_error_deg': round(float(np.percentile(np.abs(error), 95)), 4),
        'bias_deg': round(float(np.mean(error)), 4),
    }


def read_group_mapping(path, rows, allow_provisional=False, validation_only=False):
    source_groups = {}
    reviews = {}
    with Path(path).open('r', newline='', encoding='utf-8-sig') as handle:
        for item in csv.DictReader(handle):
            vid = item['video_id'].strip()
            if vid in source_groups:
                raise ValueError(f'Duplicate mapping entry: {vid}')
            group = item.get('source_recording_group', '').strip()
            if not group:
                raise ValueError(f'Missing source recording group for {vid}')
            source_groups[vid] = group
            reviews[vid] = item.get('review_status', 'UNREVIEWED').strip().upper()
    ids = {r['video_id'] for r in rows}
    if set(source_groups) != ids:
        raise ValueError(f'Group map mismatch: missing={sorted(ids-set(source_groups))}, extra={sorted(set(source_groups)-ids)}')
    unverified = [v for v in source_groups if reviews[v] != 'VERIFIED']
    if unverified and not (allow_provisional and validation_only):
        raise ValueError('UNREVIEWED recording groups: use BOTH --allow-provisional-groups and '
                         '--validation-only for a strictly exploratory convergence run; '
                         'do not mark source groups VERIFIED without evidence.')
    return source_groups, unverified


def evaluate_model(model, loader, device, mode, amp_active=False):
    model.eval()
    truth, predicted, by_video = [], [], {}
    with torch.inference_mode():
        for frames, flow, angle, ids in loader:
            frames = frames.to(device)
            flow = flow.to(device)
            with torch.autocast(device_type='cuda', enabled=True) if amp_active else nullcontext():
                prediction = model(frames, flow if mode.endswith('_flow') else None)
            expected = angle.tolist()
            output = prediction.float().cpu().tolist()
            truth.extend(expected)
            predicted.extend(output)
            for vid, actual, guess in zip(ids, expected, output):
                item = by_video.setdefault(vid, {'truth': [], 'pred': []})
                item['truth'].append(actual)
                item['pred'].append(guess)
    return metrics(truth, predicted), {vid: metrics(v['truth'], v['pred']) for vid, v in by_video.items()}


def train_evaluate(manifest, output, epochs=4, batch_size=4, seed=42, pretrained=False, modes=MODES,
                   label_origin='manual_f1_annotation', device_choice='auto', group_map=None,
                   max_train_sequences=None, max_validation_sequences=None, resume_from=None, lr=1e-3,
                   allow_provisional_groups=False, validation_only=False,
                   early_stopping_patience=0, min_delta=0.05, amp=False):
    if epochs < 1 or batch_size < 1 or lr <= 0:
        raise ValueError('Positive epochs, batch size and learning rate required')
    if early_stopping_patience < 0 or min_delta < 0:
        raise ValueError('Early stopping patience and min_delta cannot be negative')
    if device_choice not in ('auto', 'cpu', 'cuda'):
        raise ValueError('device must be auto, cpu or cuda')
    if device_choice == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested, but it is unavailable in this environment')
    device = torch.device('cuda' if (device_choice == 'cuda' or
                                   (device_choice == 'auto' and torch.cuda.is_available())) else 'cpu')
    amp_active = bool(amp and device.type == 'cuda')
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == 'cuda':
        torch.cuda.manual_seed_all(seed)
    print(f'[steering] device={device}, AMP={amp_active}, seed={seed}', flush=True)

    rows = read_manifest(manifest)
    source_groups = None
    unverified_ids = []
    if group_map:
        source_groups, unverified_ids = read_group_mapping(group_map, rows, allow_provisional_groups, validation_only)
        if resume_from:
            raise ValueError('Refusing pretrained F1 checkpoint warm-start with a new source-group map: potential test leakage')
    elif allow_provisional_groups:
        raise ValueError('--allow-provisional-groups requires --group-map')
    if resume_from and pretrained:
        raise ValueError('Checkpoint warm-start cannot be combined with --pretrained')
    if unverified_ids:
        print('[WARNING] Source groups UNREVIEWED. Validation-only exploratory convergence; NO final-test metric.', flush=True)
    if not group_map and not validation_only:
        print('[WARNING] Filename-only split: final test is NOT source-independent certified.', flush=True)

    train_rows, val_rows, test_rows = split_train_validation_test(rows, seed=seed, source_groups=source_groups)
    train_ds = WheelSequenceDataset(train_rows, window=6)
    val_ds = WheelSequenceDataset(val_rows, window=6)
    test_ds = WheelSequenceDataset(test_rows, window=6)
    if max_train_sequences is not None:
        if max_train_sequences < 1:
            raise ValueError('--max-train-sequences must be positive')
        train_ds.samples = random.Random(seed).sample(train_ds.samples, min(max_train_sequences, len(train_ds.samples)))
    if max_validation_sequences is not None:
        if max_validation_sequences < 1:
            raise ValueError('--max-validation-sequences must be positive')
        val_ds.samples = random.Random(seed+1).sample(val_ds.samples, min(max_validation_sequences, len(val_ds.samples)))
    if not train_ds or not val_ds:
        raise ValueError('At least one consecutive six-frame sequence required in train and validation')
    if not validation_only and not test_ds:
        raise ValueError('Final test has no valid six-frame sequences')

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() or any(out.with_name(f'{out.stem}_{mode}.pt').exists() for mode in modes):
        raise FileExistsError(f'Experiment output/checkpoint already exists for {out}; choose a NEW filename. '
                              'Old experiment outputs are protected.')

    split_description = ('PROVISIONAL_GROUP_DISJOINT_NOT_SOURCE_VERIFIED' if unverified_ids else
                         'USER_REVIEWED_GROUP_DISJOINT_SOURCE_INDEPENDENCE_NOT_CERTIFIED' if group_map else
                         'FILENAME_ONLY_UNVERIFIED')
    report = {
        'experiment':'steering_cv_temporal_ablation',
        'status':'exploratory_validation_only' if validation_only else 'evaluated_source_independence_unverified',
        'seed':seed,'epochs_requested':epochs,'pretrained_imagenet_backbone':pretrained,
        'training_device':str(device),'amp':amp_active,'label_origin':label_origin,
        'reference':('manually annotated visible wheel rotation, NOT official F1 steering telemetry'
                     if label_origin == 'manual_f1_annotation' else 'simulator reference; source dependent'),
        'split':split_description,
        'group_mapping':str(group_map) if group_map else None,
        'unverified_recording_ids':len(unverified_ids),
        'validation_only':validation_only,
        'resumed_from':str(resume_from) if resume_from else None,
        'max_train_sequences':max_train_sequences,
        'max_validation_sequences':max_validation_sequences,
        'train_video_ids':sorted({r['video_id'] for r in train_rows}),
        'validation_video_ids':sorted({r['video_id'] for r in val_rows}),
        'reserved_test_video_ids':sorted({r['video_id'] for r in test_rows}),
        'train_sequences':len(train_ds),'validation_sequences':len(val_ds),
        'reserved_test_sequences':len(test_ds),'models':{},
        'limitations': ('Manual visual labels, unverified source video identity, unknown FPS and underlying footage rights. '
                        'Sequence windows overlap. Do not infer real car steering sensors, causality, or source-independent accuracy.')
    }
    constant = float(np.median([seq[-1]['angle_deg'] for _, seq in train_ds.samples]))
    val_labels = [seq[-1]['angle_deg'] for _, seq in val_ds.samples]
    report['median_angle_baseline'] = {'train_median_angle_deg':round(constant, 4),
                                        'validation':metrics(val_labels, [constant]*len(val_labels))}
    for mode in modes:
        model = SteeringRegressor(mode, pretrained=pretrained, freeze_encoder=True).to(device)
        if resume_from:
            prior = Path(resume_from)
            old_checkpoint = prior.with_name(f'{prior.stem}_{mode}.pt')
            bundle = torch.load(old_checkpoint, map_location=device, weights_only=True)
            if bundle['mode'] != mode or bundle.get('metadata', {}).get('seed') != seed:
                raise ValueError(f'Checkpoint architecture/seed mismatch: {old_checkpoint}')
            if set(bundle.get('metadata', {}).get('trained_on_video_ids', [])) != set(report['train_video_ids']):
                raise ValueError('Checkpoint train IDs differ from current split; refusing potential leakage')
            model.load_state_dict(bundle['weights'])
            print(f'[warm-start] {old_checkpoint}: optimizer will be reset', flush=True)
        parameters = list(model.head.parameters())
        if mode != 'cnn':
            parameters += list(model.gru.parameters())
        optimizer = torch.optim.Adam(parameters, lr=lr)
        scaler = torch.amp.GradScaler('cuda', enabled=amp_active)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
        history, best_mae, best_epoch, no_improve = [], float('inf'), 0, 0
        checkpoint = out.with_name(f'{out.stem}_{mode}.pt')
        history_path = out.with_name(f'{out.stem}_{mode}_history.json')
        best_metrics, best_by_video = None, None
        for epoch in range(1, epochs+1):
            model.train()
            total_loss, seen = 0.0, 0
            for frames, flow, angles, ids in train_loader:
                frames, flow, angles = frames.to(device), flow.to(device), angles.to(device)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast(device_type='cuda', enabled=True) if amp_active else nullcontext():
                    predicted = model(frames, flow if mode.endswith('_flow') else None)
                    loss = nn.functional.smooth_l1_loss(predicted, angles)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                total_loss += loss.detach().item()*len(angles)
                seen += len(angles)
            mean_loss = total_loss/max(seen, 1)
            val_metrics, by_video = evaluate_model(model, val_loader, device, mode, amp_active)
            val_mae = val_metrics['mae_deg']
            improved = val_mae < best_mae - min_delta
            if improved:
                best_mae, best_epoch, no_improve = val_mae, epoch, 0
                best_metrics, best_by_video = val_metrics, by_video
                torch.save({'mode':mode,'weights':model.state_dict(),
                            'metadata':{'pretrained':pretrained,'seed':seed,'label_origin':label_origin,
                                        'trained_on_video_ids':report['train_video_ids'],
                                        'group_map':str(group_map) if group_map else None,
                                        'split':split_description,'best_epoch':best_epoch,
                                        'validation_only':validation_only}}, checkpoint)
            else:
                no_improve += 1
            history.append({'epoch':epoch,'train_smooth_l1':round(mean_loss,5),
                            'validation_mae_deg':val_metrics['mae_deg'],
                            'validation_rmse_deg':val_metrics['rmse_deg'],
                            'best_so_far_mae_deg':round(best_mae,4)})
            history_path.write_text(json.dumps({
                'mode':mode,'history':history,'seed':seed,'best_epoch':best_epoch,
                'split':split_description,'validation_only':validation_only,
                'note':'Exploratory validation convergence; sequence windows overlap; source provenance is not certified.'
            },indent=2),encoding='utf-8')
            print(f'[steering] {mode} epoch {epoch}/{epochs}: train loss={mean_loss:.3f}; '
                  f'val MAE={val_mae:.2f}°; best={best_mae:.2f}° at epoch {best_epoch}',flush=True)
            if early_stopping_patience and no_improve >= early_stopping_patience:
                print(f'[early stopping] {mode}: no improvement in {no_improve} epochs',flush=True)
                break
        report['models'][mode] = {
            'training_history':history, 'epochs_completed':len(history),
            'best_epoch':best_epoch,'validation':best_metrics,
            'by_validation_video':best_by_video,
            'saved_checkpoint':str(checkpoint),
        }
    best_mode = min(modes,key=lambda m:report['models'][m]['validation']['mae_deg'])
    report['selected_model'] = {'mode':best_mode,
                                'validation_mae_deg':report['models'][best_mode]['validation']['mae_deg'],
                                'selection_policy':'Minimum validation MAE; checkpoints saved at best validation epoch.'}
    if validation_only:
        report['selected_model']['final_test'] = {
            'status':'NOT_RUN_PROVISIONAL_SOURCE_GROUPS',
            'reason':'Test partition deliberately not evaluated without reviewed source provenance.'
        }
    else:
        test_loader = DataLoader(test_ds,batch_size=batch_size,shuffle=False,num_workers=0)
        model = SteeringRegressor(best_mode,pretrained=False,freeze_encoder=True).to(device)
        ckpt = torch.load(report['models'][best_mode]['saved_checkpoint'], map_location=device, weights_only=True)
        model.load_state_dict(ckpt['weights'])
        final, per_video = evaluate_model(model,test_loader,device,best_mode,amp_active)
        report['selected_model']['final_test'] = final
        report['selected_model']['by_final_test_video'] = per_video
        report['selected_model']['selection_policy'] += ' Test does not select the model; source independence still requires evidence.'
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True)
    p.add_argument('--output',default='results/steering_ablation.json')
    p.add_argument('--epochs',type=int,default=4)
    p.add_argument('--batch-size',type=int,default=4)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--pretrained',action='store_true')
    p.add_argument('--label-origin',choices=['manual_f1_annotation','simulator_sensor'],default='manual_f1_annotation')
    p.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    p.add_argument('--amp',action='store_true',help='Use CUDA mixed precision where CUDA is available')
    p.add_argument('--modes',nargs='+',choices=MODES,default=list(MODES))
    p.add_argument('--group-map',help='Recording-group mapping CSV')
    p.add_argument('--allow-provisional-groups',action='store_true',help='Must combine with --validation-only for UNREVIEWED groups')
    p.add_argument('--validation-only',action='store_true',help='Deliberately skip final holdout test')
    p.add_argument('--max-train-sequences',type=int)
    p.add_argument('--max-validation-sequences',type=int)
    p.add_argument('--resume-from',help='Warm-start from existing experiment; NOT permitted with a new group map')
    p.add_argument('--lr',type=float,default=1e-3)
    p.add_argument('--early-stopping-patience',type=int,default=0,help='0 disables early stopping')
    p.add_argument('--min-delta',type=float,default=0.05,help='Minimum MAE improvement in degrees')
    a=p.parse_args()
    result=train_evaluate(a.manifest,a.output,a.epochs,a.batch_size,a.seed,a.pretrained,
                          modes=a.modes,label_origin=a.label_origin,device_choice=a.device,
                          group_map=a.group_map,max_train_sequences=a.max_train_sequences,
                          max_validation_sequences=a.max_validation_sequences,resume_from=a.resume_from,
                          lr=a.lr,allow_provisional_groups=a.allow_provisional_groups,
                          validation_only=a.validation_only,early_stopping_patience=a.early_stopping_patience,
                          min_delta=a.min_delta,amp=a.amp)
    print(json.dumps({'status':result['status'],'output':a.output,
                      'selected_model':result['selected_model'],
                      'median_baseline':result['median_angle_baseline']},indent=2))


if __name__=='__main__': cli()
