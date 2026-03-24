"""Tests for melodic key sorting: key prefix in filename, no key subdirectory.

Keyless melodic samples get a 'zz' prefix so they sort after all musical keys (A-G).
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
            (s["id"], s["local_path"], s["filename"], s["tags"],
             s["sample_type"], s.get("bpm", 0), s.get("audio_key")),
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


class TestMelodicKeySorting:

    def test_melodic_with_key_gets_key_prefix_no_subdir(self):
        """Melodic sample with key should have key prefix in filename but no key subdirectory."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 40, "local_path": str(source_dir / "warm-pad.wav"),
                        "filename": "warm-pad.wav", "tags": "bass",
                        "sample_type": "loop", "bpm": 120, "audio_key": "Fm"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            # Should be in bass/loop/ (no key subdir), with key prefix in filename
            bass_loop = stage_dir / "bass" / "loop"
            assert bass_loop.exists()
            filenames = [f.name for f in bass_loop.iterdir()]
            assert "FM-120-warm-pad.wav" in filenames
            # Should NOT have a key subdirectory
            assert not (bass_loop / "FM").exists(), "Key subdirectory should not exist"

    def test_melodic_without_key_gets_zz_prefix(self):
        """Melodic sample without a key should get 'zz' prefix to sort after keyed samples."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 41, "local_path": str(source_dir / "bass-growl.wav"),
                        "filename": "bass-growl.wav", "tags": "bass",
                        "sample_type": "oneshot", "bpm": 0, "audio_key": None}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            bass_oneshot = stage_dir / "bass" / "oneshot"
            assert bass_oneshot.exists()
            filenames = [f.name for f in bass_oneshot.iterdir()]
            assert "zz-bass-growl.wav" in filenames, \
                f"Keyless melodic sample should get 'zz' prefix, got {filenames}"

    def test_keyless_sorts_after_keyed(self):
        """Keyless melodic samples (zz prefix) should sort after keyed samples (A-G prefix)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [
                {"id": 50, "local_path": str(source_dir / "bass-one.wav"),
                 "filename": "bass-one.wav", "tags": "bass",
                 "sample_type": "oneshot", "bpm": 0, "audio_key": "Cm"},
                {"id": 51, "local_path": str(source_dir / "bass-two.wav"),
                 "filename": "bass-two.wav", "tags": "bass",
                 "sample_type": "oneshot", "bpm": 0, "audio_key": "Gm"},
                {"id": 52, "local_path": str(source_dir / "bass-nokey.wav"),
                 "filename": "bass-nokey.wav", "tags": "bass",
                 "sample_type": "oneshot", "bpm": 0, "audio_key": None},
            ]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            bass_oneshot = stage_dir / "bass" / "oneshot"
            filenames = sorted(f.name for f in bass_oneshot.iterdir())
            # CM and GM should sort before zz
            assert filenames == ["CM-bass-one.wav", "GM-bass-two.wav", "zz-bass-nokey.wav"], \
                f"Expected keyed before keyless, got {filenames}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
