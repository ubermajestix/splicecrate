"""Tests for tag-based categorization.

Verifies that samples are categorized correctly based on their Splice tags,
including case insensitivity, multi-tag handling, and "other" fallback.
"""

import sqlite3
import tempfile
from pathlib import Path

from splicecrate import organizer


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def staged_files(stage_dir, category):
    """Recursively collect filenames staged under a given category folder."""
    cat_dir = stage_dir / category
    if not cat_dir.exists():
        return []
    return [p.name for p in cat_dir.rglob("*") if p.is_file()]


# ---------------------------------------------------------------------------
# Case-insensitive tag matching
# ---------------------------------------------------------------------------

class TestCaseInsensitiveMatching:

    def test_uppercase_tag_matches(self):
        """Tags stored in uppercase (e.g. 'SNARES') should still match."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 1, "local_path": str(source_dir / "snare_verb.wav"),
                        "filename": "snare_verb.wav", "tags": "SNARES",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "snare_verb.wav" in staged_files(stage_dir, "drums"), \
                "Uppercase tag 'SNARES' should map to drums category"

    def test_mixed_case_tag_matches(self):
        """Tags like 'Kicks' should match case-insensitively."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 2, "local_path": str(source_dir / "BD_Hard.wav"),
                        "filename": "BD_Hard.wav", "tags": "Kicks",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "BD_Hard.wav" in staged_files(stage_dir, "drums")


# ---------------------------------------------------------------------------
# Tag-to-category mapping
# ---------------------------------------------------------------------------

class TestTagCategoryMapping:

    def test_kicks_tag_goes_to_drums(self):
        """Samples tagged 'kicks' should land in drums/ (parent category)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 10, "local_path": str(source_dir / "kick_hard.wav"),
                        "filename": "kick_hard.wav", "tags": "kicks",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "kick_hard.wav" in staged_files(stage_dir, "drums")

    def test_snares_tag_goes_to_drums(self):
        """Samples tagged 'snares' should land in drums/."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 11, "local_path": str(source_dir / "snare_01.wav"),
                        "filename": "snare_01.wav", "tags": "snares",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "snare_01.wav" in staged_files(stage_dir, "drums")

    def test_synth_tag_is_melodic(self):
        """Samples tagged 'synth' should get key subdirectories."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 12, "local_path": str(source_dir / "pad_warm.wav"),
                        "filename": "pad_warm.wav", "tags": "synth",
                        "sample_type": "loop", "bpm": 120, "audio_key": "Cm"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "120-pad_warm.wav" in staged_files(stage_dir, "synth")
            # Should be under synth/loop/CM/
            expected = stage_dir / "synth" / "loop" / "CM" / "120-pad_warm.wav"
            assert expected.exists(), f"Expected melodic path {expected}"

    def test_multi_tag_uses_first_match(self):
        """First matching tag determines category."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 13, "local_path": str(source_dir / "groove_01.wav"),
                        "filename": "groove_01.wav", "tags": "drums,grooves",
                        "sample_type": "loop", "bpm": 95}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            # "drums" matches first -> drums category
            assert "095-groove_01.wav" in staged_files(stage_dir, "drums")


# ---------------------------------------------------------------------------
# "Other" fallback with subdirectories
# ---------------------------------------------------------------------------

class TestOtherFallback:

    def test_no_tags_goes_to_other(self):
        """Samples with no tags should go to other/."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 20, "local_path": str(source_dir / "misc_element.wav"),
                        "filename": "misc_element.wav", "tags": None,
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "misc_element.wav" in staged_files(stage_dir, "other")

    def test_unmapped_tag_becomes_other_subdir(self):
        """Tags like 'melodic stack' should become other/melodic_stack/."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 21, "local_path": str(source_dir / "stack_loop.wav"),
                        "filename": "stack_loop.wav", "tags": "soul,melodic stack",
                        "sample_type": "loop", "bpm": 85, "audio_key": "C"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            # "soul" is a genre tag (skipped), "melodic stack" becomes subdir
            assert "085-stack_loop.wav" in staged_files(stage_dir, "other/melodic_stack")

    def test_genre_only_tags_goes_to_plain_other(self):
        """Samples with only genre tags should go to other/ (not other/genre/)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 22, "local_path": str(source_dir / "vibe_01.wav"),
                        "filename": "vibe_01.wav", "tags": "soul,hip hop,rnb",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)})

            assert "vibe_01.wav" in staged_files(stage_dir, "other")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
