#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from sync_common import download_text, filter_rules, normalize_text, parse_mapping_file, read_text, validate_rule_payload, write_if_changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build derived rule files from SOURCE_MAPPING.yaml.")
    parser.add_argument("--mapping", default="SOURCE_MAPPING.yaml", help="Path to the mapping file.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Only build the named local files, for example AI.yaml.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    mapping_path = repo_root / args.mapping
    rules = filter_rules(parse_mapping_file(mapping_path), set(args.only))

    updated = 0
    skipped = 0

    for rule in rules:
        if rule.mode != "derived":
            continue
        if rule.builder != "append":
            raise ValueError(f"{rule.local_file}: unsupported builder {rule.builder}")

        content = build_append_rule(rule, repo_root)
        target = repo_root / rule.local_file
        changed = write_if_changed(target, content, dry_run=args.dry_run)
        if changed:
            updated += 1
            print(f"built {rule.local_file} with builder=append")
        else:
            skipped += 1
            print(f"unchanged {rule.local_file}")

    print(f"derived build complete: updated={updated} unchanged={skipped}")
    return 0


def build_append_rule(rule, repo_root: Path) -> str:
    upstream = normalize_text(download_text(rule.original_url))
    validate_rule_payload(upstream, f"{rule.local_file} upstream")

    append_file = rule.append_file or f"derived/{Path(rule.local_file).stem}.append.yaml"
    extras_path = repo_root / append_file
    extras = normalize_text(read_text(extras_path)).strip("\n")
    if "payload:" in extras:
        raise ValueError(f"{extras_path}: payload key is not allowed in append fragment")

    combined = upstream.rstrip("\n")
    if extras:
        combined = f"{combined}\n\n{extras}"
    combined = f"{combined}\n"
    validate_rule_payload(combined, rule.local_file)
    return combined


if __name__ == "__main__":
    raise SystemExit(main())
