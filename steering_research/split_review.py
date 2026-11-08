"""NON-CERTIFYING, image-free split preview for the F1 steering candidate manifest.

Uses exactly the same group partition function as train.py. Never changes source CSVs,
labels or checkpoint weights. Unreviewed source families remain unreviewed.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .data import split_train_validation_test


def csv_rows(path):
    with Path(path).open('r', newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def eligible_windows(rows, window=6):
    by_video = defaultdict(set)
    for row in rows:
        by_video[row['video_id']].add(int(row['frame_index']))
    count = 0
    for indexes in by_video.values():
        for i in indexes:
            if all(i - delta in indexes for delta in range(window)):
                count += 1
    return count


def generate(manifest, mapping, output_dir, similarity_csv=None, seed=42):
    rows = csv_rows(manifest)
    groups = csv_rows(mapping)
    required_manifest = {'video_id', 'frame_index', 'angle_deg', 'frame_path'}
    required_group = {'video_id', 'source_recording_group', 'review_status'}
    if not rows or not required_manifest.issubset(rows[0]):
        raise ValueError('Candidate manifest must contain video_id/frame_index/angle_deg/frame_path')
    if not groups or not required_group.issubset(groups[0]):
        raise ValueError('Group map missing video_id/source_recording_group/review_status')
    ids = [r['video_id'] for r in groups]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate video_id values in group map')
    mapping_by_id = {g['video_id']: g for g in groups}
    row_ids = {r['video_id'] for r in rows}
    if row_ids != set(ids):
        raise ValueError(f'Group map mismatches candidate manifest: missing={sorted(row_ids-set(ids))}, extra={sorted(set(ids)-row_ids)}')
    if any(not g['source_recording_group'].strip() for g in groups):
        raise ValueError('Source-group field is empty for at least one recording ID')
    if len({(r['video_id'], r['frame_index']) for r in rows}) != len(rows):
        raise ValueError('Duplicate video_id/frame_index combinations in manifest')
    srcmap = {vid: mapping_by_id[vid]['source_recording_group'].strip() for vid in ids}
    train, val, test = split_train_validation_test(rows, seed=seed, source_groups=srcmap)
    partitions = {'TRAIN': train, 'VALIDATION': val, 'TEST_RESERVED': test}
    lookup = {}
    for name, partition in partitions.items():
        for row in partition:
            vid = row['video_id']
            if vid in lookup and lookup[vid] != name:
                raise AssertionError(f'Filename ID crossed split: {vid}')
            lookup[vid] = name
    source_to_split = defaultdict(set)
    for vid, group in srcmap.items():
        source_to_split[group].add(lookup[vid])
    crossing_groups = {g: sorted(ps) for g, ps in source_to_split.items() if len(ps) != 1}
    if crossing_groups:
        raise AssertionError(f'Source group split leak: {crossing_groups}')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_vid = Counter(r['video_id'] for r in rows)
    per_video = defaultdict(list)
    for r in rows:
        per_video[r['video_id']].append(r)
    assignment_rows = []
    for vid in sorted(ids):
        g = mapping_by_id[vid]
        assignment_rows.append({
            'video_id':vid, 'source_recording_group':srcmap[vid], 'partition':lookup[vid],
            'frame_count':by_vid[vid], 'sequence_count':eligible_windows(per_video[vid]),
            'review_status':g['review_status'],
            'evidence_notes':g.get('evidence_notes', ''),
        })
    write_csv(out/'split_assignments_PREVIEW_ONLY.csv',assignment_rows,
              ['video_id','source_recording_group','partition','frame_count','sequence_count','review_status','evidence_notes'])
    risk_rows=[]
    if similarity_csv:
        similarities = csv_rows(similarity_csv)
        for r in similarities:
            a,b = r.get('video_id_a'), r.get('video_id_b')
            if a not in lookup or b not in lookup:
                continue
            if lookup[a] == lookup[b]:
                continue
            exact = r.get('pixel_identical_file','').strip().lower() in ('true','1','yes')
            risk_rows.append({
                'priority': 'P0_EXACT_IMAGE_CROSS_SPLIT' if exact else 'P1_PHASH_REVIEW_ONLY',
                'video_id_a':a,'video_id_b':b,
                'source_group_a':srcmap[a],'source_group_b':srcmap[b],
                'partition_a':lookup[a],'partition_b':lookup[b],
                'phash_distance':r.get('phash_distance',''),
                'pixel_identical_file':r.get('pixel_identical_file',''),
                'frame_a':r.get('frame_a',''),'frame_b':r.get('frame_b',''),
                'angle_a_deg':r.get('angle_a_deg',''),'angle_b_deg':r.get('angle_b_deg',''),
                'review_decision':'UNREVIEWED',
            })
    risk_rows.sort(key=lambda r:(0 if r['priority'].startswith('P0') else 1,
                                 float(r['phash_distance']) if r['phash_distance'] else 99,
                                 r['video_id_a'],r['video_id_b']))
    write_csv(out/'cross_split_visual_REVIEW.csv',risk_rows,
              ['priority','video_id_a','video_id_b','source_group_a','source_group_b',
               'partition_a','partition_b','phash_distance','pixel_identical_file',
               'frame_a','frame_b','angle_a_deg','angle_b_deg','review_decision'])
    out_counts = {name: {'frames':len(partition),'filename_groups':len({r['video_id'] for r in partition}),
                         'source_groups':len({srcmap[r['video_id']] for r in partition}),
                         'six_frame_sequences':eligible_windows(partition)}
                  for name,partition in partitions.items()}
    unreviewed = sorted(g['video_id'] for g in groups if g['review_status'].strip().upper() != 'VERIFIED')
    summary = {
        'status':'PROVISIONAL_SPLIT_PREVIEW_NOT_INDEPENDENCE_CERTIFIED',
        'source_manifest':str(manifest),'source_group_map':str(mapping),'seed':seed,
        'candidate_images':len(rows), 'filename_recording_ids':len(ids),
        'proposed_source_groups':len(source_to_split),'group_crossings':len(crossing_groups),
        'partition_counts':out_counts,'unverified_filename_ids':len(unreviewed),
        'visual_similarity_cross_split_example_rows':len(risk_rows),
        'exact_image_cross_split_example_rows':sum(r['priority'].startswith('P0') for r in risk_rows),
        'warnings':[
            'Zero group crossings validates partition logic only; it does NOT prove source-video independence.',
            'pHash candidate matches may be false positives; inspect source footage and timestamps.',
            'Never mark UNREVIEWED as VERIFIED without source evidence.',
            'Use preliminary, validation-only training on this mapping; do not publish final-test claims.',
            'Candidate sequences overlap in time and are not statistically independent examples.',
        ],
    }
    (out/'split_summary_PREVIEW_ONLY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True)
    p.add_argument('--group-map',required=True)
    p.add_argument('--similarity-csv',default=None)
    p.add_argument('--output-dir',default='results/steering_split_review')
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    print(json.dumps(generate(a.manifest,a.group_map,a.output_dir,a.similarity_csv,a.seed),indent=2))


if __name__=='__main__': main()
