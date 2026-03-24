import logging
import os
import shutil
from pathlib import Path

from . import database, manifest

log = logging.getLogger(__name__)


def build_staged_path(category_name, category_config, sample):
    """Build the relative path for a sample within the staging directory.

    Percussive categories skip key filename prefix.
    Grooves (split_by_type) get oneshot/loop subdirs even though percussive.
    Melodic categories get sample_type subdirs with key as filename prefix.
    Keyless melodic samples use 'zz' prefix to sort after all keys (A-G).
    """
    parts = [category_name]
    is_percussive = category_config.get("percussive", False)
    split_by_type = category_config.get("split_by_type", False)
    sample_type = sample["sample_type"] or "oneshot"
    key = sample["audio_key"]
    bpm = sample["bpm"]

    if is_percussive:
        if split_by_type:
            parts.append(sample_type)
        # No key subdir for percussive
    else:
        parts.append(sample_type)

    # Build filename
    filename_parts = []
    if not is_percussive:
        if key:
            filename_parts.append(key.upper())
        else:
            # "zz" sorts after all musical keys (A-G), pushing keyless samples to the end
            filename_parts.append("zz")
    if bpm and bpm != 0:
        filename_parts.append(str(int(bpm)))
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


def organize(config, hierarchy, dry_run=False):
    """Main organize routine: read DB, stage new/changed files locally."""
    conn = database.connect(config["sounds_db"])
    stage_dir = Path(config["stage_dir"])
    stage_dir.mkdir(parents=True, exist_ok=True)

    mf = manifest.load_manifest(stage_dir)
    categories = hierarchy.get("categories", hierarchy.get("sample_dirs", {}))
    categorized_ids = set()
    total_copied = 0
    total_skipped = 0

    for cat_name, cat_config in categories.items():
        samples = database.get_samples(conn, cat_config)
        copied = 0
        skipped = 0

        for sample in samples:
            sample_id = sample["id"]
            categorized_ids.add(sample_id)
            source_path = sample["local_path"]

            if not source_path or not os.path.exists(source_path):
                log.debug("Skipping %s: source file missing", sample["filename"])
                skipped += 1
                continue

            # Use a manifest key that includes category to support duplicates across categories
            manifest_key = f"{sample_id}:{cat_name}"
            if not manifest.needs_update(mf, manifest_key, source_path):
                skipped += 1
                continue

            rel_path = build_staged_path(cat_name, cat_config, sample)
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

    # Catchall: samples not matched by any category
    catchall = hierarchy.get("catchall")
    if catchall:
        catchall_name = catchall.get("dirname", "other")
        all_samples = database.get_all_samples(conn)
        catchall_copied = 0
        catchall_skipped = 0

        for sample in all_samples:
            if sample["id"] in categorized_ids:
                continue
            source_path = sample["local_path"]
            if not source_path or not os.path.exists(source_path):
                catchall_skipped += 1
                continue

            manifest_key = f"{sample['id']}:{catchall_name}"
            if not manifest.needs_update(mf, manifest_key, source_path):
                catchall_skipped += 1
                continue

            # Catchall uses a simple flat structure with bpm prefix
            filename_parts = []
            if sample["bpm"] and sample["bpm"] != 0:
                filename_parts.append(str(int(sample["bpm"])))
            filename_parts.append(sample["filename"])
            filename = "-".join(filename_parts)
            rel_path = Path(catchall_name) / (sample["sample_type"] or "oneshot") / filename

            if dry_run:
                log.info("[dry-run] Would copy: %s -> %s", source_path, rel_path)
                catchall_copied += 1
                continue

            dest_path = stage_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path = resolve_collision(dest_path)
            shutil.copy2(source_path, dest_path)
            manifest.record_file(mf, manifest_key, source_path, rel_path, catchall_name)
            catchall_copied += 1

        log.info("%s: %d new, %d skipped", catchall_name, catchall_copied, catchall_skipped)
        total_copied += catchall_copied
        total_skipped += catchall_skipped

    if not dry_run:
        manifest.save_manifest(mf, stage_dir)

    conn.close()
    log.info("Done. %d copied, %d skipped.", total_copied, total_skipped)
    return total_copied, total_skipped


def status(config, hierarchy):
    """Show category counts and new files since last run."""
    conn = database.connect(config["sounds_db"])
    stage_dir = Path(config["stage_dir"])
    mf = manifest.load_manifest(stage_dir)
    categories = hierarchy.get("categories", hierarchy.get("sample_dirs", {}))
    categorized_ids = set()

    print(f"{'Category':<16} {'Total':>6} {'Staged':>7} {'New':>5}")
    print("-" * 38)

    for cat_name, cat_config in categories.items():
        samples = database.get_samples(conn, cat_config)
        total = len(samples)
        new_count = 0
        for sample in samples:
            categorized_ids.add(sample["id"])
            manifest_key = f"{sample['id']}:{cat_name}"
            source = sample["local_path"]
            if source and os.path.exists(source) and manifest.needs_update(mf, manifest_key, source):
                new_count += 1
        staged = total - new_count
        print(f"{cat_name:<16} {total:>6} {staged:>7} {new_count:>5}")

    # Catchall
    catchall = hierarchy.get("catchall")
    if catchall:
        all_samples = database.get_all_samples(conn)
        uncategorized = [s for s in all_samples if s["id"] not in categorized_ids]
        cat_name = catchall.get("dirname", "other")
        new_count = sum(
            1 for s in uncategorized
            if s["local_path"] and os.path.exists(s["local_path"])
            and manifest.needs_update(mf, f"{s['id']}:{cat_name}", s["local_path"])
        )
        print(f"{cat_name:<16} {len(uncategorized):>6} {len(uncategorized) - new_count:>7} {new_count:>5}")

    conn.close()
    if mf["last_run"]:
        print(f"\nLast organized: {mf['last_run']}")
    else:
        print("\nNever organized (no manifest found)")
