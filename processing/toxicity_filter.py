"""
Filtr toksyczności (placeholder):
- Prosty scoring słów zakazanych; w produkcji użyć Detoxify/Perspective.
Wejście: data/clean/clean_pii.jsonl
Wyjście: data/clean/clean_safe.jsonl
Odrzucone: data/quarantine/toxic.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_pii.jsonl"
OUT_PATH = ROOT / "data" / "clean" / "clean_safe.jsonl"
QUAR = ROOT / "data" / "quarantine" / "toxic.jsonl"

BLOCKLIST: List[str] = ["nienawiść", "mowa nienawiści", "zabij", "gwałt", "ludobójstwo"]


def is_toxic(text: str) -> bool:
    low = text.lower()
    return any(word in low for word in BLOCKLIST)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUAR.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    dropped = 0
    with IN_PATH.open("r", encoding="utf-8") as fin, \
            OUT_PATH.open("w", encoding="utf-8") as fout, \
            QUAR.open("w", encoding="utf-8") as fq:
        for line in fin:
            rec: Dict[str, Any] = json.loads(line)
            txt = rec.get("clean_text", "")
            if is_toxic(txt):
                fq.write(json.dumps(rec, ensure_ascii=False) + "\n")
                dropped += 1
                continue
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
    print(f"Kept={kept}, Dropped={dropped}")
    print(f"Zapisano: {OUT_PATH}, odrzucone: {QUAR}")


if __name__ == "__main__":
    main()

