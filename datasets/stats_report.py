"""
Prosty raport statystyk:
- Zlicza wpisy per source, kraj, typ.
- Raport zapisuje do docs/stats_report.md
Wejście: data/clean/clean_safe.jsonl
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_safe.jsonl"
REPORT = ROOT / "docs" / "stats_report.md"


def main() -> None:
    by_source = collections.Counter()
    by_country = collections.Counter()
    by_type = collections.Counter()
    total = 0
    with IN_PATH.open("r", encoding="utf-8") as fin:
        for line in fin:
            rec = json.loads(line)
            total += 1
            by_source[rec.get("source", "?")] += 1
            by_country[rec.get("country", "?")] += 1
            by_type[rec.get("type", "?")] += 1

    lines = [
        "# Stats report",
        "",
        f"Total records: {total}",
        "",
        "## By source",
    ]
    for k, v in by_source.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## By country")
    for k, v in by_country.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## By type")
    for k, v in by_type.most_common():
        lines.append(f"- {k}: {v}")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Zapisano raport: {REPORT}")


if __name__ == "__main__":
    main()

