"""Audit exact duplicate labelled F1 onboard frames without changing source data.

This is a supplemental audit, NOT proof that non-identical frames are independent.
Usage (from project root):
  python audit_f1_exact_duplicate_labels.py --manifest steering_data/f1_steering_manifest.csv \
      --previous-results results/steering_ablation_gpu.json \
      --group-map recording_groups_PROPOSED_NOT_VERIFIED.csv \
      --output-dir results/f1_cv_exact_audit
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def split_from_results(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    report = json.loads(path.read_text(encoding='utf-8'))
    split_map = {}
    for key, split_name in (('train_video_ids', 'TRAIN'),
                            ('validation_video_ids', 'VALIDATION'),
                            ('test_video_ids', 'TEST')):
        for video_id in report.get(key, []):
            if video_id in split_map:
                raise ValueError(f'video_id appears in multiple original splits: {video_id}')
            split_map[video_id] = split_name
    return split_map


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--previous-results', help='Optional original experiment JSON to identify cross-split duplicates')
    parser.add_argument('--group-map', help='Optional proposed (unverified) recording grouping CSV')
    parser.add_argument('--output-dir', default='results/f1_cv_exact_audit')
    args = parser.parse_args()
    manifest = Path(args.manifest).resolve()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    items = read_csv(manifest)
    needed = {'video_id', 'frame_path', 'angle_deg'}
    if not items or not needed.issubset(items[0]):
        raise ValueError(f'Manifest requires columns {sorted(needed)}')
    original_splits = split_from_results(Path(args.previous_results) if args.previous_results else None)
    proposed = {}
    if args.group_map:
        for row in read_csv(Path(args.group_map)):
            proposed[row['video_id']] = row.get('source_recording_group', '').strip()

    by_hash: dict[str, list[dict]] = defaultdict(list)
    missing = []
    for index, row in enumerate(items, 1):
        path = Path(row['frame_path'])
        if not path.is_absolute():
            path = manifest.parent / path
        if not path.is_file():
            missing.append(str(path))
            continue
        entry = dict(row)
        entry['path'] = str(path)
        entry['angle'] = float(row['angle_deg'])
        entry['old_split'] = original_splits.get(row['video_id'], 'NOT_IN_OLD_REPORT')
        entry['proposed_group'] = proposed.get(row['video_id'], '')
        by_hash[sha256_file(path)].append(entry)
        if index % 500 == 0:
            print(f'Hashed {index}/{len(items)} frames...', flush=True)
    if missing:
        report = {'status': 'FAILED_MISSING_IMAGES', 'missing_count': len(missing), 'missing_examples': missing[:20]}
        (out / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        raise FileNotFoundError(f'{len(missing)} images missing. See {out / "summary.json"}. Example: {missing[0]}')

    duplicate_clusters = []
    duplicate_rows = []
    conflicting_clusters = []
    cross_split_clusters = []
    grouped_cross_split = []
    for digest, records in by_hash.items():
        if len(records) < 2:
            continue
        angles = [r['angle'] for r in records]
        distinct_vids = sorted(set(r['video_id'] for r in records))
        all_splits = sorted(set(r['old_split'] for r in records) - {'NOT_IN_OLD_REPORT'})
        groups = sorted(set(r['proposed_group'] for r in records if r['proposed_group']))
        spread = max(angles) - min(angles)
        conflict = spread > 0.01
        crosses = len(all_splits) > 1
        crosses_groups = len(groups) > 1
        cluster = {
            'sha256': digest, 'image_count': len(records),
            'video_ids': ';'.join(distinct_vids),
            'old_splits': ';'.join(all_splits),
            'proposed_groups': ';'.join(groups),
            'label_min_deg': round(min(angles), 4),
            'label_max_deg': round(max(angles), 4),
            'label_spread_deg': round(spread, 4),
            'label_conflict': conflict,
            'crosses_original_split': crosses,
            'crosses_proposed_groups': crosses_groups,
            'review_priority': 'P0_EXACT_CROSS_SPLIT' if crosses else ('P1_LABEL_CONFLICT' if conflict else 'P2_EXACT_DUPLICATE'),
        }
        duplicate_clusters.append(cluster)
        if conflict:
            conflicting_clusters.append(cluster)
        if crosses:
            cross_split_clusters.append(cluster)
        if crosses_groups:
            grouped_cross_split.append(cluster)
        for r in records:
            duplicate_rows.append({
                'sha256': digest, 'video_id': r['video_id'],
                'frame_index': r.get('frame_index', ''),
                'angle_deg': r['angle'],
                'old_split': r['old_split'],
                'proposed_group': r['proposed_group'],
                'frame_path': r['path'],
            })

    cluster_fields = ['sha256', 'image_count', 'video_ids', 'old_splits', 'proposed_groups',
                      'label_min_deg', 'label_max_deg', 'label_spread_deg', 'label_conflict',
                      'crosses_original_split', 'crosses_proposed_groups', 'review_priority']
    row_fields = ['sha256', 'video_id', 'frame_index', 'angle_deg', 'old_split', 'proposed_group', 'frame_path']
    duplicate_clusters.sort(key=lambda d: (not d['crosses_original_split'], not d['label_conflict'], -d['image_count']))
    write_csv(out / 'exact_duplicate_clusters.csv', duplicate_clusters, cluster_fields)
    write_csv(out / 'exact_duplicate_frames.csv', duplicate_rows, row_fields)
    write_csv(out / 'priority_cross_split_duplicates.csv', cross_split_clusters, cluster_fields)
    write_csv(out / 'conflicting_labels.csv', conflicting_clusters, cluster_fields)
    write_csv(out / 'cross_proposed_groups.csv', grouped_cross_split, cluster_fields)
    group_counter = Counter(r['video_id'] for r in items)
    game_like = sorted(v for v in group_counter if 'juego' in v.lower())
    summary = {
        'status': 'EXACT_HASH_AUDIT_COMPLETE_NOT_INDEPENDENCE_CERTIFICATION',
        'total_manifest_rows': len(items),
        'hashed_rows': sum(map(len, by_hash.values())),
        'unique_exact_images': len(by_hash),
        'duplicate_image_clusters': len(duplicate_clusters),
        'duplicate_image_rows': len(duplicate_rows),
        'duplicate_clusters_with_label_disagreement': len(conflicting_clusters),
        'duplicate_clusters_crossing_original_split': len(cross_split_clusters),
        'duplicate_clusters_crossing_proposed_groups': len(grouped_cross_split),
        'filename_groups': len(group_counter),
        'proposed_groups': len(set(g for g in proposed.values() if g)),
        'potential_game_domain_groups': game_like,
        'potential_game_domain_frames': sum(group_counter[g] for g in game_like),
        'notes': [
            'Byte-identical images in different splits establish actual leakage.',
            'Matching hashes with differing labels establish annotation inconsistencies.',
            'Different hashes do NOT prove independence. Perceptual, temporal and source-URL review is still required.',
            'Proposed group IDs are filename-derived, UNVERIFIED. Do not mark them VERIFIED without source evidence.',
            'This audit writes reports only; it never deletes images, edits labels, changes splits or trains models.',
        ],
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    print(f'Audit files written to: {out}', flush=True)

if __name__ == '__main__':
    main()
