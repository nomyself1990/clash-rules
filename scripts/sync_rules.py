#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from sync_common import download_text, filter_rules, normalize_text, parse_mapping_file, validate_rule_payload, write_if_changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync mirrored rule files from SOURCE_MAPPING.yaml.")
    parser.add_argument("--mapping", default="SOURCE_MAPPING.yaml", help="Path to the mapping file.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only sync the named local files, for example Apple.yaml China.yaml.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    mapping_path = repo_root / args.mapping
    rules = filter_rules(parse_mapping_file(mapping_path), set(args.only))

    updated = 0
    skipped = 0
    derived = 0

    for rule in rules:
        if rule.mode == "derived":
            derived += 1
            print(f"skip derived {rule.local_file} ({rule.builder or 'unknown builder'})")
            continue
        if rule.mode != "mirror":
            raise ValueError(f"{rule.local_file}: unsupported mode {rule.mode}")

        text = normalize_text(download_text(rule.original_url))
        validate_rule_payload(text, rule.local_file)

        target = repo_root / rule.local_file
        changed = write_if_changed(target, text, dry_run=args.dry_run)
        if changed:
            updated += 1
            print(f"updated {rule.local_file} from {rule.source}")
        else:
            skipped += 1
            print(f"unchanged {rule.local_file}")

    print(f"mirror sync complete: updated={updated} unchanged={skipped} derived_skipped={derived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
