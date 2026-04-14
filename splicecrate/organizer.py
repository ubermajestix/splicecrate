import logging
import os
import shutil
from collections import defaultdict
from pathlib import Path

from . import database, manifest
from .categories import categorize_sample
from .keys import resolve_key_prefix

log = logging.getLogger(__name__)


def build_staged_path(category, is_percussive, sample):
    """Build the relative path for a sample within the staging directory.

    Rules for drums:
    - Drums oneshots: drums/one-shots/subcategory/filename.wav
    - Drums loops:    drums/loops/subcategory/BPM-filename.wav  (BPM zero-padded to 3 digits)

    Rules for other categories:
    - Percussive oneshots:  category/oneshot/filename.wav
    - Percussive loops:     category/loop/BPM-filename.wav  (BPM zero-padded to 3 digits)
    - Melodic oneshots:     category/oneshot/KEY-filename.wav
    - Melodic loops:        category/loop/KEY-BPM-filename.wav  (BPM zero-padded to 3 digits)
    - Keyless melodic:      'zz' prefix sorts after all musical keys (A-G)
    """
    sample_type = sample["sample_type"] or "oneshot"
    key = sample["audio_key"]
    bpm = sample["bpm"]
    is_loop = sample_type == "loop"

    # Special handling for drums: drums/loops/kicks or drums/one-shots/kicks
    if category.startswith("drums/"):
        base_category = "drums"
        subcategory = category.split("/", 1)[1]  # Extract the subcategory (kicks, snares, etc.)
        type_folder = "loops" if is_loop else "one-shots"
        parts = [base_category, type_folder, subcategory]
    else:
        parts = [category]
        parts.append(sample_type)

    # Build filename
    filename_parts = []
    if not is_percussive:
        key_prefix = resolve_key_prefix(key, sample["filename"])
        if key_prefix:
            filename_parts.append(key_prefix)
        else:
            # "zz" sorts after all musical keys (A-G), pushing keyless samples to the end
            filename_parts.append("zz")
    if is_loop and bpm and bpm != 0:
        filename_parts.append(f"{int(bpm):03d}")
    filename_parts.append(sample["filename"])
    filename = "-".join(filename_parts)

    parts.append(filename)
    return Path(*parts)


def resolve_collision(dest_path):
    """If dest_path exists, append _2, _3, etc. to stem."""
    if not dest_path.exists():
        return dest_path
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    i = 2
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def organize(config, dry_run=False):
    """Main organize routine: read DB, categorize by tags, stage new/changed files."""
    conn = database.connect(config["sounds_db"])
    stage_dir = Path(config["stage_dir"])
    stage_dir.mkdir(parents=True, exist_ok=True)

    mf = manifest.load_manifest(stage_dir)
    all_samples = database.get_all_samples(conn)

    # Group samples by category
    by_category = defaultdict(list)
    for sample in all_samples:
        cat, is_percussive = categorize_sample(sample["tags"])
        by_category[cat].append((sample, is_percussive))

    total_copied = 0
    total_skipped = 0

    # Process each discovered category
    for cat_name in sorted(by_category.keys()):
        samples = by_category[cat_name]
        copied = 0
        skipped = 0

        for sample, is_percussive in samples:
            sample_id = sample["id"]
            source_path = sample["local_path"]

            if not source_path or not os.path.exists(source_path):
                log.debug("Skipping %s: source file missing", sample["filename"])
                skipped += 1
                continue

            manifest_key = f"{sample_id}:{cat_name}"
            if not manifest.needs_update(mf, manifest_key, source_path):
                skipped += 1
                continue

            rel_path = build_staged_path(cat_name, is_percussive, sample)
            dest_path = stage_dir / rel_path

            if dry_run:
                log.info("[dry-run] Would copy: %s -> %s", source_path, rel_path)
                copied += 1
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path = resolve_collision(dest_path)
            shutil.copy2(source_path, dest_path)
            manifest.record_file(mf, manifest_key, source_path, rel_path, cat_name)
            copied += 1

        log.info("%s: %d new, %d skipped", cat_name, copied, skipped)
        total_copied += copied
        total_skipped += skipped

    if not dry_run:
        manifest.save_manifest(mf, stage_dir)

    conn.close()
    log.info("Done. %d copied, %d skipped.", total_copied, total_skipped)
    return total_copied, total_skipped


def status(config):
    """Show category counts and new files since last run."""
    conn = database.connect(config["sounds_db"])
    stage_dir = Path(config["stage_dir"])
    mf = manifest.load_manifest(stage_dir)
    all_samples = database.get_all_samples(conn)

    # Group samples by category
    by_category = defaultdict(list)
    for sample in all_samples:
        cat, _ = categorize_sample(sample["tags"])
        by_category[cat].append(sample)

    print(f"{'Category':<24} {'Total':>6} {'Staged':>7} {'New':>5}")
    print("-" * 46)

    for cat_name in sorted(by_category.keys()):
        samples = by_category[cat_name]
        total = len(samples)
        new_count = 0
        for sample in samples:
            manifest_key = f"{sample['id']}:{cat_name}"
            source = sample["local_path"]
            if source and os.path.exists(source) and manifest.needs_update(mf, manifest_key, source):
                new_count += 1
        staged = total - new_count
        print(f"{cat_name:<24} {total:>6} {staged:>7} {new_count:>5}")

    conn.close()
    if mf["last_run"]:
        print(f"\nLast organized: {mf['last_run']}")
    else:
        print("\nNever organized (no manifest found)")
