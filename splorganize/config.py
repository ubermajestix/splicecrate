import tomllib
import argparse
from pathlib import Path


DEFAULTS = {
    "splice_dir": Path.home() / "Documents" / "Splice" / "Samples",
    "stage_dir": Path.home() / "Documents" / "Splice" / "Splorganized",
    "dest_dir": None,
    "sounds_db": Path(__file__).resolve().parent.parent / "sounds.db",
}

CONFIG_PATH = Path.home() / ".splorganizer" / "splorganizer.toml"


def load_config_file():
    """Load config from ~/.splorganizer/splorganizer.toml if it exists."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def build_config(cli_args=None):
    """Build final config by merging defaults, config file, and CLI args."""
    config = dict(DEFAULTS)

    # Layer 2: config file overrides
    file_config = load_config_file()
    for key in DEFAULTS:
        if key in file_config:
            config[key] = Path(file_config[key])

    # Layer 3: CLI overrides
    if cli_args:
        for key in DEFAULTS:
            val = getattr(cli_args, key, None)
            if val is not None:
                config[key] = Path(val)

    # Ensure Path types
    for key in ["splice_dir", "stage_dir", "sounds_db"]:
        config[key] = Path(config[key])
    if config["dest_dir"] is not None:
        config["dest_dir"] = Path(config["dest_dir"])

    return config


def build_parser():
    parser = argparse.ArgumentParser(
        prog="splorganize",
        description="Organize Splice samples for 1010music Blackbox",
    )
    parser.add_argument("--db", dest="sounds_db", help="Path to sounds.db")
    parser.add_argument("--stage-dir", dest="stage_dir", help="Local staging directory")
    parser.add_argument("--dest-dir", dest="dest_dir", help="SD card / final destination")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    sub = parser.add_subparsers(dest="command")

    org = sub.add_parser("organize", help="Read sounds.db and stage files locally")
    org.add_argument("--dry-run", action="store_true", help="Show what would be copied without copying")

    syn = sub.add_parser("sync", help="Copy staged files to SD card destination")
    syn.add_argument("--dry-run", action="store_true", help="Show what would be copied without copying")

    sub.add_parser("status", help="Show category counts and new files since last run")
    sub.add_parser("discover", help="Scan sounds.db and show discovered categories")

    return parser
