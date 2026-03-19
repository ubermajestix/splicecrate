"""Tests for two categorization bug fixes:

  A) Case-insensitive regex matching — filenames like SNARE_01.wav or HiHat_Open.wav
     should match their categories regardless of case.

  B) OR logic for tag_regex + file_regex — a file that matches *either* the filename
     pattern *or* the tag should be categorized, not require both.

Both fixes live in splorganize/database.py.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

from splicecrate import database, organizer


# ---------------------------------------------------------------------------
# Shared helpers (same pattern as test_kick_organization.py)
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


def load_hierarchy():
    hier_path = Path(__file__).resolve().parent.parent / "hierarchy.json"
    with open(hier_path) as f:
        return json.load(f)


def staged_files(stage_dir, category):
    """Recursively collect filenames staged under a given category folder."""
    cat_dir = stage_dir / category
    if not cat_dir.exists():
        return []
    return [p.name for p in cat_dir.rglob("*") if p.is_file()]


def other_files(stage_dir):
    return staged_files(stage_dir, "other")


# ---------------------------------------------------------------------------
# Fix A: Case-insensitive matching
# ---------------------------------------------------------------------------

class TestCaseInsensitiveMatching:

    def test_uppercase_snare_filename_with_tag(self):
        """SNARE_01.wav tagged 'snares' should go to snares, not other."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 1, "local_path": str(source_dir / "SNARE_01.wav"),
                        "filename": "SNARE_01.wav", "tags": "snares",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "SNARE_01.wav" in staged_files(stage_dir, "snares"), \
                "Uppercase snare filename should be in snares"
            assert "SNARE_01.wav" not in other_files(stage_dir), \
                "Uppercase snare filename should not be in other"

    def test_mixed_case_hihat_filename_with_tag(self):
        """HiHat_Open.wav tagged 'hats' should go to hats, not other."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 2, "local_path": str(source_dir / "HiHat_Open.wav"),
                        "filename": "HiHat_Open.wav", "tags": "hats",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "HiHat_Open.wav" in staged_files(stage_dir, "hats"), \
                "Mixed-case hihat filename should be in hats"
            assert "HiHat_Open.wav" not in other_files(stage_dir), \
                "Mixed-case hihat filename should not be in other"

    def test_uppercase_kick_filename_with_tag(self):
        """BD_Hard.wav tagged 'kicks' should go to kicks, not other."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 3, "local_path": str(source_dir / "BD_Hard.wav"),
                        "filename": "BD_Hard.wav", "tags": "kicks",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "BD_Hard.wav" in staged_files(stage_dir, "kicks"), \
                "Uppercase BD filename should be in kicks"
            assert "BD_Hard.wav" not in other_files(stage_dir)

    def test_uppercase_tag_with_matching_filename(self):
        """Tags stored in uppercase (e.g. 'SNARES') should still match."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 4, "local_path": str(source_dir / "snare_verb.wav"),
                        "filename": "snare_verb.wav", "tags": "SNARES",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "snare_verb.wav" in staged_files(stage_dir, "snares"), \
                "Uppercase tag 'SNARES' should still match snares category"
            assert "snare_verb.wav" not in other_files(stage_dir)


# ---------------------------------------------------------------------------
# Fix B: OR logic — file_regex OR tag_regex is sufficient
# ---------------------------------------------------------------------------

class TestOrLogicMatching:

    def test_snare_filename_no_tags_goes_to_snares(self):
        """snare_heavy.wav with no tags should be caught by file_regex alone."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 10, "local_path": str(source_dir / "snare_heavy.wav"),
                        "filename": "snare_heavy.wav", "tags": None,
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "snare_heavy.wav" in staged_files(stage_dir, "snares"), \
                "snare filename with no tags should still go to snares via file_regex"
            assert "snare_heavy.wav" not in other_files(stage_dir), \
                "snare filename with no tags should not end up in other"

    def test_hihat_filename_no_tags_goes_to_hats(self):
        """hh_closed_01.wav with no tags should be caught by file_regex alone."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 11, "local_path": str(source_dir / "hh_closed_01.wav"),
                        "filename": "hh_closed_01.wav", "tags": None,
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "hh_closed_01.wav" in staged_files(stage_dir, "hats"), \
                "hh filename with no tags should go to hats via file_regex"
            assert "hh_closed_01.wav" not in other_files(stage_dir)

    def test_kick_filename_empty_tags_goes_to_kicks(self):
        """kick_punch.wav with empty string tags should be caught by file_regex."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 12, "local_path": str(source_dir / "kick_punch.wav"),
                        "filename": "kick_punch.wav", "tags": "",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "kick_punch.wav" in staged_files(stage_dir, "kicks"), \
                "kick filename with empty tags should go to kicks via file_regex"
            assert "kick_punch.wav" not in other_files(stage_dir)

    def test_snare_tag_unusual_filename_still_categorized(self):
        """A file tagged 'snares' with an unusual filename should still go to snares."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 13, "local_path": str(source_dir / "percy_element_01.wav"),
                        "filename": "percy_element_01.wav", "tags": "snares",
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "percy_element_01.wav" in staged_files(stage_dir, "snares"), \
                "File tagged 'snares' should go to snares even with unusual filename"
            assert "percy_element_01.wav" not in other_files(stage_dir)

    def test_melodic_loop_no_filename_match_uses_tag(self):
        """A synth loop with tag 'synth' but no keyword in filename should be categorized."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 14, "local_path": str(source_dir / "atmosphere_loop_01.wav"),
                        "filename": "atmosphere_loop_01.wav", "tags": "synth",
                        "sample_type": "loop", "bpm": 120, "audio_key": "Cm"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            # build_staged_path uppercases the key, so "Cm" becomes "CM"
            assert "CM-120-atmosphere_loop_01.wav" in staged_files(stage_dir, "synth"), \
                "Synth-tagged loop should go to synth regardless of filename"
            assert "CM-120-atmosphere_loop_01.wav" not in other_files(stage_dir)


# ---------------------------------------------------------------------------
# Fix A + B combined: uppercase filename, no tags
# ---------------------------------------------------------------------------

class TestCombinedFixes:

    def test_uppercase_snare_no_tags(self):
        """SNARE_Heavy.wav with no tags needs both fixes: case-insensitive file_regex
        to match the filename, and OR logic so tag isn't required."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 20, "local_path": str(source_dir / "SNARE_Heavy.wav"),
                        "filename": "SNARE_Heavy.wav", "tags": None,
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "SNARE_Heavy.wav" in staged_files(stage_dir, "snares"), \
                "Uppercase snare with no tags should go to snares (requires both fixes)"
            assert "SNARE_Heavy.wav" not in other_files(stage_dir)

    def test_uppercase_hihat_loop_no_tags(self):
        """HH_Open_Loop.wav with no tags should land in hats (hats allows loops)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 21, "local_path": str(source_dir / "HH_Open_Loop.wav"),
                        "filename": "HH_Open_Loop.wav", "tags": None,
                        "sample_type": "loop", "bpm": 135}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "135-HH_Open_Loop.wav" in staged_files(stage_dir, "hats"), \
                "Uppercase hihat loop with no tags should go to hats"
            assert "135-HH_Open_Loop.wav" not in other_files(stage_dir)

    def test_unrelated_file_still_goes_to_other(self):
        """A file with no recognizable filename or tags should still go to other."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = tmp_path / "source"
            source_dir.mkdir()

            samples = [{"id": 30, "local_path": str(source_dir / "misc_element_xyz.wav"),
                        "filename": "misc_element_xyz.wav", "tags": None,
                        "sample_type": "oneshot"}]
            create_source_files(tmp_path, samples)
            db_path = make_test_db(tmp_path, samples)
            stage_dir = tmp_path / "staged"

            organizer.organize({"sounds_db": str(db_path), "stage_dir": str(stage_dir)}, load_hierarchy())

            assert "misc_element_xyz.wav" in other_files(stage_dir), \
                "Truly unrecognizable file should still end up in other"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
