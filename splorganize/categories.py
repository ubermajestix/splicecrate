"""Splice tag-to-category mapping.

Maps Splice's subcategory tags to their parent categories, matching
the taxonomy shown on Splice's sounds page. Categories are discovered
from each user's sounds.db rather than hardcoded in a config file.

Tags that don't map to any known parent end up in "other" with the
tag name as a subdirectory.
"""

# Top-level categories and the Splice subcategory tags that belong to them.
# Source: Splice sounds page category browser.
CATEGORY_TAGS = {
    "drums": {
        "drums", "kicks", "snares", "hats", "claps", "toms", "cymbals",
        "breaks", "fills", "acoustic drums", "808",
        # Common tag variants found in sounds.db
        "rides", "rims", "closed", "open", "tops", "crash",
        "rolls", "snaps", "sidestick",
    },
    "percussion": {
        "percussion", "shakers", "grooves", "tambourine", "bongos", "cowbells",
        "woodblock", "bells", "conga", "djembe", "timbales",
        # Common tag variants
        "mallets", "claves", "congas", "brushes",
    },
    "vocals": {
        "female vocals", "male vocals", "vocal fx", "spoken word",
        "vocoder", "vocal phrases", "screams", "vocal shouts",
        "whisper vocals", "dialogue",
        # Common tag variants
        "vocals", "female", "male", "shouts", "phrases",
        "hooks", "adlib", "choir", "chants",
    },
    "fx": {
        "noise", "risers", "downers", "sweeps", "impacts",
        "atmospheres", "textures", "reverse", "field recordings",
        "fx vocals",
        # Common tag variants
        "fx", "foley", "transitions", "found sounds",
        "siren", "lasers",
    },
    "bass": {
        "sub", "electric bass", "acid bass",
        "wobble", "pulse", "reese",
        # "bass" itself is handled specially since it appears as a
        # subcategory under multiple parents (synth, strings, etc.)
        "bass",
    },
    "synth": {
        "synth", "leads", "pads", "arp", "stabs", "chords",
        "plucks", "analog", "synth melody",
    },
    "guitar": {
        "guitar", "electric guitar", "riffs", "rhythm",
        "guitar melody", "slide",
    },
    "keys": {
        "keys", "piano", "electric piano", "wurlitzer", "organ",
        "clavinet", "keys melody", "classical", "hammond",
    },
    "brass and woodwinds": {
        "brass & woodwinds", "saxophone", "trumpet", "trombone",
        "flute", "ensemble", "harmonica", "horns",
    },
    "strings": {
        "strings", "violin", "cello", "viola", "orchestral",
        "staccato", "strings melody", "harp",
    },
}

# Categories where samples are percussive (no musical key in path/filename).
PERCUSSIVE_CATEGORIES = {"drums", "percussion"}

# Build a reverse lookup: tag -> parent category
_TAG_TO_CATEGORY = {}
for _cat, _tags in CATEGORY_TAGS.items():
    for _tag in _tags:
        # First category to claim a tag wins
        if _tag not in _TAG_TO_CATEGORY:
            _TAG_TO_CATEGORY[_tag] = _cat


def tag_to_category(tag):
    """Map a single tag to its parent category, or None if unknown."""
    return _TAG_TO_CATEGORY.get(tag.lower().strip())


# Genre/descriptor tags that should not be used as "other" subdirectory names.
# These are too broad to be useful as folder names.
_GENRE_TAGS = {
    "soul", "hip hop", "rnb", "house", "deep house", "drum and bass",
    "breakbeat", "reggaeton", "dancehall", "reggae", "jazz", "neo soul",
    "pop", "edm", "techno", "tech house", "ambient", "downtempo",
    "lo-fi hip hop", "trap", "dubstep", "indie", "rock", "indie rock",
    "funk", "disco", "blues", "boom bap", "minimal techno",
    "uk garage", "bass music", "future garage", "jungle", "90s",
    "electro house", "future bass", "dub", "indie electronic",
    "chillout", "carribbean", "caribbean", "latin american",
}


def categorize_sample(tags_str):
    """Given a comma-separated tags string, return the best parent category.

    Priority: first matching tag wins (Splice puts the most specific
    tag first in the comma-separated list).

    Returns (category_name, is_percussive) or ("other/subtag", False) if no
    known tag matches. For "other", the first non-genre tag is used as a
    subdirectory name.
    """
    if not tags_str:
        return "other", False

    tags = [t.strip().lower() for t in tags_str.split(",")]

    for tag in tags:
        cat = tag_to_category(tag)
        if cat:
            return cat, cat in PERCUSSIVE_CATEGORIES

    # No known category — pick the first non-genre tag as subdirectory
    for tag in tags:
        if tag not in _GENRE_TAGS:
            subdir = tag.replace(" ", "_")
            return f"other/{subdir}", False

    return "other", False


def discover_categories(conn):
    """Scan a sounds.db and return categories with sample counts.

    Returns a dict: {category_name: count} for all categories that
    have at least one sample with a local_path.
    """
    from collections import Counter

    rows = conn.execute(
        "SELECT tags FROM samples WHERE local_path IS NOT NULL"
    ).fetchall()

    counts = Counter()
    for row in rows:
        cat, _ = categorize_sample(row["tags"])
        counts[cat] += 1

    return dict(counts.most_common())
