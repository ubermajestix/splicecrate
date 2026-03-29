"""Tests for splicecrate.keys: key normalization, filename parsing, prefix resolution."""

from splicecrate.keys import normalize_key, parse_key_from_filename, resolve_key_prefix


# ---------------------------------------------------------------------------
# normalize_key
# ---------------------------------------------------------------------------

class TestNormalizeKey:

    def test_minor_preserved(self):
        assert normalize_key("Cm") == "Cm"

    def test_bare_note_defaults_to_major(self):
        assert normalize_key("C") == "CM"

    def test_minor_lowercase_note(self):
        assert normalize_key("fm") == "Fm"

    def test_major_explicit(self):
        assert normalize_key("Amaj") == "AM"

    def test_flat_minor(self):
        assert normalize_key("Bbm") == "Bbm"

    def test_sharp_minor(self):
        assert normalize_key("F#m") == "F#m"

    def test_sharp_major(self):
        assert normalize_key("F#maj") == "F#M"

    def test_flat_major_explicit(self):
        assert normalize_key("Ebmaj") == "EbM"

    def test_minor_long_form(self):
        assert normalize_key("Cmin") == "Cm"

    def test_minor_full_word(self):
        assert normalize_key("Cminor") == "Cm"

    def test_major_full_word(self):
        assert normalize_key("Cmajor") == "CM"

    def test_uppercase_m_means_major(self):
        assert normalize_key("CM") == "CM"

    def test_none_returns_none(self):
        assert normalize_key(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_key("") is None

    def test_whitespace_returns_none(self):
        assert normalize_key("  ") is None


# ---------------------------------------------------------------------------
# parse_key_from_filename
# ---------------------------------------------------------------------------

class TestParseKeyFromFilename:

    def test_cm_at_end(self):
        assert parse_key_from_filename("D_OLIVER_wet_vocal_oh_01_120_Cm.wav") == "Cm"

    def test_amaj_at_end(self):
        assert parse_key_from_filename("LYRE_vocal_chop_dj_ah_pop_drop_wet_110_Amaj.wav") == "AM"

    def test_bbm_at_end(self):
        assert parse_key_from_filename("SO_NS_90_vocals_takealittlebit_cranberry_Bbm.wav") == "Bbm"

    def test_no_key_in_filename(self):
        assert parse_key_from_filename("kick_hard_01.wav") is None

    def test_hyphen_separated(self):
        assert parse_key_from_filename("bass-loop-120-Fm.wav") == "Fm"

    def test_sharp_key_in_filename(self):
        assert parse_key_from_filename("synth_pad_F#m.wav") == "F#m"


# ---------------------------------------------------------------------------
# resolve_key_prefix
# ---------------------------------------------------------------------------

class TestResolveKeyPrefix:

    def test_db_key_with_scale_used_directly(self):
        assert resolve_key_prefix("Cm", "some_file_120_Cm.wav") == "Cm"

    def test_db_key_with_major_scale(self):
        assert resolve_key_prefix("Amaj", "some_file.wav") == "AM"

    def test_bare_db_key_falls_back_to_filename_minor(self):
        assert resolve_key_prefix("C", "loop_120_Cm.wav") == "Cm"

    def test_bare_db_key_falls_back_to_filename_major(self):
        assert resolve_key_prefix("A", "loop_110_Amaj.wav") == "AM"

    def test_bare_db_key_no_filename_info_defaults_major(self):
        assert resolve_key_prefix("C", "some_loop.wav") == "CM"

    def test_no_db_key_uses_filename(self):
        assert resolve_key_prefix(None, "vocal_120_Bbm.wav") == "Bbm"

    def test_no_db_key_no_filename_returns_none(self):
        assert resolve_key_prefix(None, "kick_hard.wav") is None

    def test_empty_db_key_uses_filename(self):
        assert resolve_key_prefix("", "pad_Fm.wav") == "Fm"
