"""Musical key normalization and filename parsing.

Convention: Note is uppercase, accidental preserved (b/#), scale = M (major) or m (minor).
Examples: CM = C Major, Cm = C minor, Bbm = Bb minor, F#M = F# Major.
"""

import re

# Note letter + optional accidental + optional scale indicator
_KEY_RE = re.compile(
    r'^([A-Ga-g])'                      # note letter
    r'([b#]?)'                          # optional accidental
    r'(m|min|minor|maj|major|M)?$'      # optional scale
)


def normalize_key(raw_key):
    """Normalize a key string into canonical Note + Scale format.

    Returns None for empty/None input. Bare notes (no scale) default to major.
    """
    if not raw_key or not raw_key.strip():
        return None
    raw_key = raw_key.strip()
    m = _KEY_RE.match(raw_key)
    if not m:
        return raw_key.upper()  # unrecognized format, fallback
    note = m.group(1).upper()
    accidental = m.group(2)
    scale_str = m.group(3) or ''

    if scale_str in ('m', 'min', 'minor'):
        scale = 'm'
    else:
        scale = 'M'

    return f"{note}{accidental}{scale}"


def parse_key_from_filename(filename):
    """Extract a musical key from the last segments of a filename.

    Looks at the last two underscore/hyphen-separated segments of the stem
    (before the file extension) for a recognizable key pattern.
    """
    stem = filename.rsplit('.', 1)[0]
    segments = re.split(r'[_\-]', stem)
    for seg in reversed(segments[-3:]):
        if _KEY_RE.match(seg):
            return normalize_key(seg)
    return None


def _has_scale_indicator(raw_key):
    """Check whether a raw key string includes an explicit scale indicator."""
    m = _KEY_RE.match(raw_key.strip())
    if not m:
        return False
    return m.group(3) is not None


def resolve_key_prefix(audio_key, filename):
    """Determine the key prefix for a sample's staged filename.

    Uses audio_key from the DB as the primary source. If the DB key is a bare
    note (no scale indicator), falls back to parsing the filename for a more
    specific key. Returns None if no key info is found anywhere.
    """
    if audio_key and audio_key.strip():
        normalized = normalize_key(audio_key)
        if _has_scale_indicator(audio_key):
            return normalized
        # Bare note — try filename for scale info
        from_filename = parse_key_from_filename(filename)
        if from_filename and from_filename[0] == normalized[0]:
            return from_filename
        return normalized  # default to major
    # No DB key — try filename
    return parse_key_from_filename(filename)
