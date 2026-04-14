"""Test that kick/drum samples (oneshots and loops) are organized correctly.

Kicks are a subcategory tag under the 'drums' parent category and get their own
subfolder: drums/one-shots/kicks/ for oneshots, drums/loops/kicks/ for loops with BPM prefix.
"""

import sqlite3
import tempfile
from pathlib import Path

from splicecrate import organizer


def make_test_db(tmp_path, samples):
    """Create a minimal sounds.db with the given sample rows."""
    db_path = tmp_path / "sounds.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE samples (
            id INTEGER PRIMARY KEY,
            local_path TEXT,
            attr_hash TEXT,
            dir TEXT,
            audio_key TEXT,
            bpm REAL,
            chord_type TEXT,
            duration REAL,
            file_hash TEXT,
            sas_id TEXT,
            filename TEXT,
            genre TEXT,
            pack_uuid TEXT,
            sample_type TEXT,
            tags TEXT,
            popularity INTEGER,
            purchased_at TEXT,
            last_modified_at TEXT,
            waveform_url TEXT,
            provider_name TEXT
        )
    """)
    for s in samples:
        conn.execute(
            "INSERT INTO samples (id, local_path, filename, tags, sample_type, bpm, audio_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s["id"], s["local_path"], s["filename"], s["tags"], s["sample_type"], s.get("bpm", 0), s.get("audio_key")),
        )
    conn.commit()
    conn.close()
    return db_path


def create_source_files(tmp_path, samples):
    """Create dummy source wav files so the organizer can copy them."""
    for s in samples:
        p = Path(s["local_path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"RIFF" + b"\x00" * 40)


def test_kick_oneshots_in_drums_oneshot():
    """Kick oneshots should land in drums/one-shots/kicks/."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        samples = [
            {"id": 1, "local_path": str(source_dir / "kick-hard.wav"),
             "filename": "kick-hard.wav", "tags": "kicks",
             "sample_type": "oneshot", "bpm": 0},
            {"id": 2, "local_path": str(source_dir / "bd-808.wav"),
             "filename": "bd-808.wav", "tags": "kicks",
             "sample_type": "oneshot", "bpm": 0},
        ]
        create_source_files(tmp_path, samples)
        db_path = make_test_db(tmp_path, samples)
        stage_dir = tmp_path / "staged"

        organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

        assert (stage_dir / "drums" / "one-shots" / "kicks" / "kick-hard.wav").exists()
        assert (stage_dir / "drums" / "one-shots" / "kicks" / "bd-808.wav").exists()


def test_kick_loops_with_bpm_prefix():
    """Kick loops should land in drums/loops/kicks/ with zero-padded BPM prefix."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        samples = [
            {"id": 10, "local_path": str(source_dir / "kick-pattern.wav"),
             "filename": "kick-pattern.wav", "tags": "kicks",
             "sample_type": "loop", "bpm": 128},
            {"id": 11, "local_path": str(source_dir / "bd-groove.wav"),
             "filename": "bd-groove.wav", "tags": "kicks",
             "sample_type": "loop", "bpm": 92},
        ]
        create_source_files(tmp_path, samples)
        db_path = make_test_db(tmp_path, samples)
        stage_dir = tmp_path / "staged"

        organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

        assert (stage_dir / "drums" / "loops" / "kicks" / "128-kick-pattern.wav").exists()
        assert (stage_dir / "drums" / "loops" / "kicks" / "092-bd-groove.wav").exists()


def test_kick_loop_no_bpm():
    """Kick loop with no BPM should land in drums/loops/kicks/ without prefix."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        samples = [
            {"id": 20, "local_path": str(source_dir / "kick-loop-raw.wav"),
             "filename": "kick-loop-raw.wav", "tags": "kicks",
             "sample_type": "loop", "bpm": 0},
        ]
        create_source_files(tmp_path, samples)
        db_path = make_test_db(tmp_path, samples)
        stage_dir = tmp_path / "staged"

        organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

        assert (stage_dir / "drums" / "loops" / "kicks" / "kick-loop-raw.wav").exists()


def test_kick_mixed_oneshots_and_loops():
    """Oneshots and loops should go in separate subdirs under drums/one-shots/kicks/ and drums/loops/kicks/."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        samples = [
            {"id": 30, "local_path": str(source_dir / "kick-one.wav"),
             "filename": "kick-one.wav", "tags": "kicks",
             "sample_type": "oneshot", "bpm": 0},
            {"id": 31, "local_path": str(source_dir / "kick-loop.wav"),
             "filename": "kick-loop.wav", "tags": "kicks",
             "sample_type": "loop", "bpm": 175},
        ]
        create_source_files(tmp_path, samples)
        db_path = make_test_db(tmp_path, samples)
        stage_dir = tmp_path / "staged"

        organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

        assert (stage_dir / "drums" / "one-shots" / "kicks" / "kick-one.wav").exists()
        assert (stage_dir / "drums" / "loops" / "kicks" / "175-kick-loop.wav").exists()


if __name__ == "__main__":
    test_kick_oneshots_in_drums_oneshot()
    test_kick_loops_with_bpm_prefix()
    test_kick_loop_no_bpm()
    test_kick_mixed_oneshots_and_loops()
    print("All kick organization tests passed!")
