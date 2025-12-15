"""
Prosty scrubber PII (regex placeholder):
- Usuwa e-maile i numery telefonów w podstawowym formacie.
Wejście: data/clean/clean_dedup.jsonl
Wyjście: data/clean/clean_pii.jsonl
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_dedup.jsonl"
OUT_PATH = ROOT / "data" / "clean" / "clean_pii.jsonl"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\\+?\\d[\\d\\s\\-]{7,}\\d")


def redact(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    return text


def process(rec: Dict[str, Any]) -> Dict[str, Any]:
    txt = rec.get("clean_text", "")
    rec["clean_text"] = redact(txt)
    return rec


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with IN_PATH.open("r", encoding="utf-8") as fin, OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            rec = process(rec)
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Zapisano: {OUT_PATH}")


if __name__ == "__main__":
    main()

