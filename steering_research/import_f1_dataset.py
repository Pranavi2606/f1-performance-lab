"""Convert daniel-saed/F1-steering-angle-dataset into an auditable sequence manifest.

This dataset contains manual/derived image annotations, NOT official steering telemetry.
Do not treat numeric suffixes as a known frame rate. No images/labels are redistributed.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

DATASET = 'daniel-saed/F1-steering-angle-dataset'
RECORDING_PATTERN = re.compile(r'^(?P<recording>.+)_(?P<frame>\d+)$')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')


def parse_recording(image_name: str) -> tuple[str, int] | None:
    m = RECORDING_PATTERN.fullmatch(Path(image_name).stem)
    if not m:
        return None
    return m.group('recording'), int(m.group('frame'))


def get_angle(row: dict, priority: str = 'steering_angle') -> tuple[float | None, str | None]:
    # Do NOT silently clip >180 deg: original labels and curated labels may differ.
    for key in (priority, 'steering_angle_original' if priority == 'steering_angle' else 'steering_angle'):
        text = (row.get(key) or '').strip()
        if not text:
            continue
        try:
            x = float(text)
        except ValueError:
            continue
        if math.isfinite(x):
            return x, key
    return None, None


def convert(annotations: str | Path, images_dir: str | Path, output: str | Path,
            *, strict_images: bool = False, max_angle_abs: float | None = None) -> dict:
    annotations = Path(annotations)
    images_dir = Path(images_dir)
    output = Path(output)
    if not annotations.is_file():
        raise FileNotFoundError(annotations)
    if max_angle_abs is not None and max_angle_abs <= 0:
        raise ValueError('max_angle_abs must be >0')
    entries = []
    reasons = Counter()
    label_sources = Counter()
    outliers = []
    with annotations.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'img_name', 'steering_angle', 'steering_angle_original'}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f'Expected source columns {sorted(required)}')
        for row in reader:
            image_name = (row.get('img_name') or '').strip()
            parsed = parse_recording(image_name)
            if parsed is None:
                reasons['unparseable_img_name'] += 1
                continue
            group, idx = parsed
            label, origin = get_angle(row)
            if label is None:
                reasons['missing_valid_label'] += 1
                continue
            if abs(label) > 180:
                outliers.append({'image': image_name, 'angle_deg': label, 'source_field': origin})
            if max_angle_abs is not None and abs(label) > max_angle_abs:
                reasons['outside_selected_angle_range'] += 1
                continue
            candidate = None
            for ext in IMAGE_EXTENSIONS:
                p = images_dir / (image_name + ext)
                if p.is_file():
                    candidate = p
                    break
            if candidate is None:
                reasons['missing_image'] += 1
                if strict_images:
                    raise FileNotFoundError(f'Image for {image_name} not found in {images_dir}')
                continue
            entries.append({'video_id': group, 'frame_index': idx, 'frame_path': str(candidate.resolve()),
                            'angle_deg': label, 'label_source': origin})
            label_sources[origin] += 1
    # Avoid duplicate frame indices within a recording (e.g. annotations duplicated in CSV).
    unique = {}
    for row in entries:
        key = (row['video_id'], row['frame_index'])
        if key in unique:
            reasons['duplicate_recording_frame'] += 1
            continue
        unique[key] = row
    entries = sorted(unique.values(), key=lambda r: (r['video_id'], r['frame_index']))
    recordings = defaultdict(list)
    for row in entries:
        recordings[row['video_id']].append(row)
    consecutive_6 = sum(max(0, length - 5) for rows in recordings.values()
                        for length in consecutive_run_lengths([r['frame_index'] for r in rows]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['video_id', 'frame_index', 'frame_path', 'angle_deg'])
        writer.writeheader()
        writer.writerows({k: r[k] for k in writer.fieldnames} for r in entries)
    report = {
        'status': 'manifest_prepared' if entries else 'unavailable',
        'dataset': DATASET,
        'measurement_type': 'manually annotated wheel angle from F1 onboard frames; NOT official steering telemetry',
        'label_precedence': 'steering_angle followed by steering_angle_original',
        'recording_group_rule': 'filename stem before final _NNNN suffix; grouping is inferred and requires manual verification',
        'frame_rate_known': False,
        'sequence_warning': 'Consecutive numeric suffixes do not prove equally spaced video timestamps, continuous footage, or a known FPS.',
        'images_found': len(entries),
        'recording_groups': len(recordings),
        'six_frame_contiguous_sequences': consecutive_6,
        'angles_outside_180_before_optional_exclusion': len(outliers),
        'angle_outlier_examples': outliers[:12],
        'excluded': dict(reasons),
        'label_sources_used': dict(label_sources),
        'minimum_angle_deg': min((r['angle_deg'] for r in entries), default=None),
        'maximum_angle_deg': max((r['angle_deg'] for r in entries), default=None),
        'manifest': str(output),
        'training_ready': len(recordings) >= 3 and consecutive_6 > 0,
        'rights': 'Dataset card says MIT; underlying F1 footage rights are not established. Do not redistribute images or extracted clips without permission.',
    }
    output.with_suffix('.audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def consecutive_run_lengths(indices: list[int]) -> list[int]:
    if not indices:
        return []
    ordered = sorted(set(indices))
    sizes, current = [], 1
    for a, b in zip(ordered, ordered[1:]):
        if b == a + 1:
            current += 1
        else:
            sizes.append(current)
            current = 1
    sizes.append(current)
    return sizes


def download_and_convert(directory: str | Path, manifest: str | Path, *, token: str | None = None, max_workers: int = 4):
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError('Install optional dependency: pip install huggingface_hub') from exc
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    # Do not commit image files; use a local, gitignored steering_data directory.
    root = Path(snapshot_download(repo_id=DATASET, repo_type='dataset', local_dir=str(path), token=token,
                                  max_workers=max_workers))
    return convert(root/'dataset_backup.csv', root/'all_frames', manifest)


def main():
    p = argparse.ArgumentParser(description='Audit and import the public annotated F1 steering frame dataset')
    p.add_argument('--dataset-root', default='steering_data/f1_steering_angle_dataset')
    p.add_argument('--manifest', default='steering_data/f1_steering_manifest.csv')
    p.add_argument('--download', action='store_true', help='Download official dataset repository through huggingface_hub')
    p.add_argument('--strict-images', action='store_true')
    p.add_argument('--max-angle-abs', type=float, default=None, help='Optional exclusion threshold; disclosed in audit')
    args = p.parse_args()
    root = Path(args.dataset_root)
    report = (download_and_convert(root, args.manifest) if args.download else
              convert(root/'dataset_backup.csv', root/'all_frames', args.manifest,
                      strict_images=args.strict_images, max_angle_abs=args.max_angle_abs))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
