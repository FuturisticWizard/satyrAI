"""
Checker licencji (manual-first):
- Wczytuje docs/whitelist.yaml
- Dodaje pole license_status na podstawie ręcznie wprowadzonych wartości (placeholder)
- Generuje raport markdown z tym co jest oznaczone jako restricted/check.

Automatyczne sprawdzenie licencji nie jest wiarygodne, należy ręcznie wpisać
`license: cc|permissive|restricted` po inspekcji Terms/FAQ.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "docs" / "whitelist.yaml"
REPORT = ROOT / "docs" / "license_report.md"


def load_whitelist() -> List[Dict[str, Any]]:
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("whitelist.yaml musi być listą wpisów")
    return data


def build_report(entries: List[Dict[str, Any]]) -> str:
    lines = [
        "# License report (manual status)",
        "",
        "| name | feed | license | notes |",
        "| --- | --- | --- | --- |",
    ]
    for e in entries:
        lines.append(
            f"| {e.get('name','')} | {e.get('feed','')} | {e.get('license','?')} | {e.get('notes','')} |"
        )
    lines.append("")
    lines.append("> Uzupełnij `license` po ręcznej weryfikacji Terms/FAQ.")
    return "\n".join(lines)


def main() -> None:
    entries = load_whitelist()
    report = build_report(entries)
    REPORT.write_text(report, encoding="utf-8")
    print(f"Zapisano raport: {REPORT}")


if __name__ == "__main__":
    main()

