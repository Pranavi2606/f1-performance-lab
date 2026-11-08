"""Create a REVERSIBLE candidate F1 steering subset after the exact-hash audit.

Not a leakage certification or a source-recording verification.
Retains source images and original manifest. Produces a new CSV manifest,
quarantine CSV, and an audit summary; excludes the six conflicting exact-hash
clusters completely and, by default, the suspected game-rendered footage.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

GAME_VIDEO_IDS = {
    'hamilton-juego3', 'leclerc-juego2', 'norris-juego1',
    'russel-juego1', 'verstappen-juego1', 'verstappen-juego4',
}


def load_csv(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f'Missing CSV headers: {path}')
        return list(reader), list(reader.fieldnames)


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def create(manifest, duplicate_frames, output_manifest, output_quarantine,
           output_summary, exclude_game=True, proposed_map=None, output_proposed_map=None):
    manifest = Path(manifest)
    output_manifest = Path(output_manifest)
    if manifest.resolve() == output_manifest.resolve():
        raise ValueError('Refusing to overwrite the original manifest.')
    if manifest.resolve().parent != output_manifest.resolve().parent:
        raise ValueError('Output manifest must be in the original manifest directory: relative image paths rely on this.')
    rows, fields = load_csv(manifest)
    necessary = {'video_id','frame_index','frame_path','angle_deg'}
    if not necessary.issubset(fields):
        raise ValueError(f'Manifest missing columns: {necessary-set(fields)}')
    duplicates, dup_fields = load_csv(duplicate_frames)
    necessary_dup = {'sha256','video_id','frame_index','angle_deg'}
    if not necessary_dup.issubset(dup_fields):
        raise ValueError(f'Exact-duplicate report missing: {necessary_dup-set(dup_fields)}')
    by_sha = {}
    for d in duplicates:
        by_sha.setdefault(d['sha256'], []).append(d)
    # Quarantine ONLY hashes with conflicts among byte-identical images.
    conflicts = {h: ds for h,ds in by_sha.items()
                 if len(ds)>1 and len({float(d['angle_deg']) for d in ds})>1}
    exclusions = {}
    for sha, ds in conflicts.items():
        for d in ds:
            key=(d['video_id'],int(d['frame_index']))
            if key in exclusions:
                raise ValueError(f'Unexpected repeated conflict key {key}')
            exclusions[key] = (sha,float(d['angle_deg']))
    kept=[]
    quarantined=[]
    reasons=Counter()
    matched=set()
    for row in rows:
        key=(row['video_id'],int(row['frame_index']))
        reason = None
        if key in exclusions:
            sha, expected_label = exclusions[key]
            if abs(float(row['angle_deg']) - expected_label)>1e-5:
                raise ValueError(f'Label mismatch for {key}; refusing to filter a modified manifest')
            matched.add(key)
            reason = f'CONFLICTING_EXACT_DUPLICATE:{sha}'
        elif exclude_game and row['video_id'] in GAME_VIDEO_IDS:
            reason = 'POSSIBLE_GAME_RENDERED_FOOTAGE_UNVERIFIED'
        if reason:
            quarantined.append({**row,'quarantine_reason':reason})
            reasons[reason.split(':')[0]]+=1
        else:
            kept.append(row)
    if matched != set(exclusions):
        raise ValueError(f'Expected {len(exclusions)} conflict entries, found {len(matched)}; '
                         f'missing={sorted(set(exclusions)-matched)}. No outputs were written.')
    if not kept:
        raise ValueError('No rows left after exclusion')
    write_csv(output_manifest,kept,fields)
    write_csv(output_quarantine,quarantined,fields+['quarantine_reason'])
    filtered_group_map_info = None
    if proposed_map:
        if not output_proposed_map:
            raise ValueError('Supply --output-proposed-map together with --proposed-map')
        group_rows,group_fields=load_csv(proposed_map)
        wanted={row['video_id'] for row in kept}
        filtered_group_rows=[r for r in group_rows if r.get('video_id') in wanted]
        if {r['video_id'] for r in filtered_group_rows}!=wanted:
            raise ValueError('Proposed map does not cover all candidate video IDs; no group-map written')
        # This is a NON-VERIFIED review map, not a training clearance.
        for r in filtered_group_rows:
            if r.get('review_status','').upper()=='VERIFIED':
                raise ValueError('Input proposed mapping marked VERIFIED; review separately before using this helper')
        write_csv(output_proposed_map,filtered_group_rows,group_fields)
        filtered_group_map_info={'file':str(output_proposed_map), 'rows':len(filtered_group_rows),
                                 'proposed_groups':len({r.get('source_recording_group','') for r in filtered_group_rows}),
                                 'verification_status':'UNREVIEWED - NOT TRAINING CLEARED'}
    summary={
        'status':'CANDIDATE_SUBSET_NOT_LEAKAGE_CERTIFIED',
        'source_manifest':str(manifest),
        'candidate_manifest':str(output_manifest),
        'quarantine_csv':str(output_quarantine),
        'source_rows':len(rows),
        'candidate_rows':len(kept),
        'quarantined_rows':len(quarantined),
        'quarantined_conflicting_exact_duplicate_rows':sum(v for k,v in reasons.items() if k=='CONFLICTING_EXACT_DUPLICATE'),
        'quarantined_potential_game_rows':reasons['POSSIBLE_GAME_RENDERED_FOOTAGE_UNVERIFIED'],
        'original_filename_groups':len({r['video_id'] for r in rows}),
        'candidate_filename_groups':len({r['video_id'] for r in kept}),
        'candidate_video_ids':sorted({r['video_id'] for r in kept}),
        'label_conflict_hash_clusters':len(conflicts),
        'filtered_proposed_group_map': filtered_group_map_info,
        'important_limits':[
            'The original images and manifest are not edited or deleted.',
            'Game footage exclusion is based on suspected provenance from filename and sampled visuals, NOT source-recording verification.',
            'A source-recording audit and perceptual/temporal duplicate review are still required before independent test claims.',
            'Do not reuse weights trained on the original potentially leaked split for final evaluation.',
            'Filtered manifest keeps the original image paths; the underlying files must remain accessible.',
            'Do not mark proposed recording groups VERIFIED merely because this filtering step passed.'
        ]
    }
    out=Path(output_summary)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'candidate_video_ids'},indent=2))
    return summary


def main():
    p=argparse.ArgumentParser(description='Create a non-destructive candidate steering dataset after exact-image audit')
    p.add_argument('--manifest',default='steering_data/f1_steering_manifest.csv')
    p.add_argument('--duplicate-frames',default='results/f1_cv_exact_audit/exact_duplicate_frames.csv')
    p.add_argument('--output-manifest',default='steering_data/f1_steering_candidate_real_review.csv')
    p.add_argument('--output-quarantine',default='results/f1_cv_exact_audit/quarantined_entries.csv')
    p.add_argument('--output-summary',default='results/f1_cv_exact_audit/candidate_subset_summary.json')
    p.add_argument('--include-game',action='store_true',help='Keep the 6 possible game-rendered groups (still unverified)')
    p.add_argument('--proposed-map',default=None,help='Optional UNREVIEWED review-mapping CSV for candidate IDs')
    p.add_argument('--output-proposed-map',default='steering_data/recording_groups_candidate_UNREVIEWED.csv')
    a=p.parse_args()
    create(a.manifest,a.duplicate_frames,a.output_manifest,a.output_quarantine,
           a.output_summary,not a.include_game, a.proposed_map, a.output_proposed_map)

if __name__=='__main__': main()
