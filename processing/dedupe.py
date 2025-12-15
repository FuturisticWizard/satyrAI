"""
Prosta deduplikacja:
- Hash pełny + opcjonalnie prosty simhash (placeholder).
Wejście: data/clean/clean.jsonl
Wyjście: data/clean/clean_dedup.jsonl
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Set

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean.jsonl"
OUT_PATH = ROOT / "data" / "clean" / "clean_dedup.jsonl"


def full_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen: Set[str] = set()
    kept = 0
    with IN_PATH.open("r", encoding="utf-8") as fin, OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec: Dict[str, Any] = json.loads(line)
            text = rec.get("clean_text", "")
            h = full_hash(text)
            if h in seen:
                continue
            seen.add(h)
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
    print(f"Zapisano: {OUT_PATH} (kept={kept}, unique_hashes={len(seen)})")


if __name__ == "__main__":
    main()

