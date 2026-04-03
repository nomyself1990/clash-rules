#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


USER_AGENT = "clash-rules-sync/1.0"


@dataclass(frozen=True)
class RuleMapping:
    local_file: str
    original_url: str
    source: str
    mode: str = "mirror"
    builder: str | None = None
    note: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "RuleMapping":
        missing = [key for key in ("local_file", "original_url", "source") if key not in data]
        if missing:
            raise ValueError(f"mapping entry missing required keys: {', '.join(missing)}")
        return cls(
            local_file=data["local_file"],
            original_url=data["original_url"],
            source=data["source"],
            mode=data.get("mode", "mirror"),
            builder=data.get("builder"),
            note=data.get("note"),
        )


def parse_mapping_file(path: Path) -> list[RuleMapping]:
    rules: list[RuleMapping] = []
    current: dict[str, str] | None = None

    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "rules:":
            continue

        if stripped.startswith("- "):
            if current is not None:
                rules.append(RuleMapping.from_dict(current))
            current = {}
            key, value = _parse_key_value(stripped[2:], lineno)
            current[key] = value
            continue

        if current is None:
            raise ValueError(f"{path}:{lineno}: unexpected content outside rules list")

        key, value = _parse_key_value(stripped, lineno)
        current[key] = value

    if current is not None:
        rules.append(RuleMapping.from_dict(current))

    if not rules:
        raise ValueError(f"{path}: no rules found")
    return rules


def _parse_key_value(text: str, lineno: int) -> tuple[str, str]:
    key, separator, value = text.partition(":")
    if not separator:
        raise ValueError(f"invalid mapping syntax at line {lineno}: {text}")
    return key.strip(), _strip_quotes(value.strip())


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def download_text(url: str, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def normalize_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized = "\n".join(line.rstrip() for line in lines).strip("\n")
    return f"{normalized}\n"


def validate_rule_payload(text: str, context: str) -> None:
    payload_seen = False
    entries_seen = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "payload:":
            payload_seen = True
            continue
        if payload_seen and stripped.startswith("- "):
            entries_seen = True
            break

    if not payload_seen:
        raise ValueError(f"{context}: missing payload block")
    if not entries_seen:
        raise ValueError(f"{context}: payload block has no entries")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_if_changed(path: Path, content: str, dry_run: bool = False) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    if not dry_run:
        path.write_text(content, encoding="utf-8")
    return True


def filter_rules(rules: Iterable[RuleMapping], only: set[str]) -> list[RuleMapping]:
    if not only:
        return list(rules)
    return [rule for rule in rules if rule.local_file in only]
