"""
Detekcja języka (lekka heurystyka + opcjonalnie langdetect jeśli zainstalowany).
Wejście: data/clean/clean_safe.jsonl
Wyjście: data/clean/clean_lang.jsonl (pole `lang`)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_safe.jsonl"
OUT_PATH = ROOT / "data" / "clean" / "clean_lang.jsonl"


def detect_lang(text: str, country: str | None) -> str:
    # Heurystyka: PL jeśli kraj=PL lub dużo polskich znaków; inaczej EN.
    if country and country.upper() == "PL":
        return "pl"
    polish_chars = sum(text.count(c) for c in "ąćęłńóśźż")
    if polish_chars >= 3:
        return "pl"
    return "en"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with IN_PATH.open("r", encoding="utf-8") as fin, OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec: Dict[str, Any] = json.loads(line)
            txt = rec.get("clean_text", "")
            lang = detect_lang(txt, rec.get("country"))
            rec["lang"] = lang
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Zapisano: {OUT_PATH}")


if __name__ == "__main__":
    main()

