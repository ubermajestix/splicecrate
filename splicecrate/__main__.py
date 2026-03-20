import logging
import sys

from .config import build_parser, build_config
from .organizer import organize, status
from .sync import sync_to_destination


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )

    if not args.command:
        parser.print_help()
        return

    config = build_config(args)

    if args.command == "organize":
        if not config["sounds_db"].exists():
            logging.error("sounds.db not found at %s", config["sounds_db"])
            sys.exit(1)
        organize(config, dry_run=args.dry_run)

    elif args.command == "sync":
        if config["dest_dir"] is None:
            logging.error("No destination directory specified. Use --dest-dir or set dest_dir in config.")
            sys.exit(1)
        sync_to_destination(config["stage_dir"], config["dest_dir"], dry_run=args.dry_run)

    elif args.command == "status":
        if not config["sounds_db"].exists():
            logging.error("sounds.db not found at %s", config["sounds_db"])
            sys.exit(1)
        status(config)

    elif args.command == "discover":
        if not config["sounds_db"].exists():
            logging.error("sounds.db not found at %s", config["sounds_db"])
            sys.exit(1)
        from . import database
        from .categories import discover_categories
        conn = database.connect(config["sounds_db"])
        counts = discover_categories(conn)
        conn.close()
        print(f"{'Category':<24} {'Samples':>8}")
        print("-" * 34)
        for cat, count in counts.items():
            print(f"{cat:<24} {count:>8}")
        print("-" * 34)
        print(f"{'Total':<24} {sum(counts.values()):>8}")


if __name__ == "__main__":
    main()
