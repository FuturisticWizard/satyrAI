"""
Normalizacja treści:
- Usuwa tagi HTML, dekoduje encje, normalizuje whitespace.
Wejście: JSONL z `data.raw` (pole data.summary / raw.content)
Wyjście: JSONL do data/clean/clean.jsonl
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rss_raw.jsonl"
OUT = ROOT / "data" / "clean" / "clean.jsonl"

TAG_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ")


def normalize(text: str) -> str:
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text).strip()
    return text


def process_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    data = rec.get("data", {})
    summary = data.get("summary") or ""
    content = summary
    content = strip_html(content)
    content = normalize(content)
    rec["clean_text"] = content
    return rec


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with RAW.open("r", encoding="utf-8") as fin, OUT.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            rec = process_record(rec)
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Zapisano: {OUT}")


if __name__ == "__main__":
    main()

