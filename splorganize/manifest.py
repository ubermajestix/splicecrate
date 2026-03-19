import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

MANIFEST_FILENAME = ".splorganizer_manifest.json"


def manifest_path(stage_dir):
    return Path(stage_dir) / MANIFEST_FILENAME


def load_manifest(stage_dir):
    """Load existing manifest or return empty structure."""
    path = manifest_path(stage_dir)
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
        log.info("Loaded manifest with %d entries", len(data.get("files", {})))
        return data
    return {"version": 1, "last_run": None, "files": {}}


def save_manifest(mf, stage_dir):
    """Write manifest atomically (write tmp, then rename)."""
    mf["last_run"] = datetime.now(timezone.utc).isoformat()
    path = manifest_path(stage_dir)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(mf, f, indent=2)
    # Atomic rename (on Windows, need to remove dest first)
    if path.exists():
        path.unlink()
    tmp_path.rename(path)
    log.info("Saved manifest with %d entries", len(mf.get("files", {})))


def needs_update(mf, sample_id, source_path):
    """Check if a sample needs to be (re-)copied."""
    key = str(sample_id)
    if key not in mf["files"]:
        return True
    entry = mf["files"][key]
    try:
        current_mtime = os.path.getmtime(source_path)
    except OSError:
        return False  # source file missing, skip
    return current_mtime != entry.get("source_mtime")


def record_file(mf, sample_id, source_path, staged_relative, category):
    """Record a file in the manifest."""
    try:
        mtime = os.path.getmtime(source_path)
    except OSError:
        mtime = 0
    mf["files"][str(sample_id)] = {
        "source": str(source_path),
        "staged_path": str(staged_relative),
        "source_mtime": mtime,
        "category": category,
    }
