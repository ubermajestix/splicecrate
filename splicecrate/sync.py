import logging
import shutil
from pathlib import Path

from .manifest import MANIFEST_FILENAME

log = logging.getLogger(__name__)


def sync_to_destination(stage_dir, dest_dir, dry_run=False):
    """Copy staged files to destination (SD card), skipping files already present with matching size."""
    stage_dir = Path(stage_dir)
    dest_dir = Path(dest_dir)

    if not stage_dir.exists():
        log.error("Stage directory does not exist: %s", stage_dir)
        return 0, 0

    if not dest_dir.exists():
        log.error("Destination directory does not exist: %s", dest_dir)
        return 0, 0

    copied = 0
    skipped = 0

    for staged_file in stage_dir.rglob("*"):
        if not staged_file.is_file():
            continue
        # Don't sync the manifest file
        if staged_file.name == MANIFEST_FILENAME:
            continue

        relative = staged_file.relative_to(stage_dir)
        dest_file = dest_dir / relative

        if dest_file.exists() and dest_file.stat().st_size == staged_file.stat().st_size:
            skipped += 1
            continue

        if dry_run:
            log.info("[dry-run] Would copy: %s", relative)
            copied += 1
            continue

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_file, dest_file)
        copied += 1

    action = "Would copy" if dry_run else "Copied"
    log.info("%s %d files, skipped %d (already present)", action, copied, skipped)
    return copied, skipped
