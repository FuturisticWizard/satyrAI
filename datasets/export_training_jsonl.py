"""
Eksport do formatu treningowego (draft):
- Wejście: data/clean/clean_safe.jsonl lub data/clean/clean_tagged.jsonl (jeśli uruchomiono tagger/lang_detect)
- Wyjście: data/curated/training_candidates.jsonl
- Struktura rekordu:
    {
      "id": ...,
      "source": ...,
      "lang": "pl"|"en" (z pola `lang` jeśli jest, inaczej heurystyka),
      "title": ...,
      "text": ...,
      "meta": {feed, country, type, license, topics?, tones?}
    }
Uwaga: w produkcji dodać prawdziwą detekcję języka (fastText/CLD3) oraz pełny tagger.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_tagged.jsonl"
OUT_PATH = ROOT / "data" / "curated" / "training_candidates.jsonl"


def detect_lang(country: str | None) -> str:
    if country and country.upper() == "PL":
        return "pl"
    return "en"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # jeśli clean_tagged nie istnieje, fallback na clean_safe
    path = IN_PATH if IN_PATH.exists() else ROOT / "data" / "clean" / "clean_safe.jsonl"
    with path.open("r", encoding="utf-8") as fin, OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec: Dict[str, Any] = json.loads(line)
            data = rec.get("data", {})
            title = data.get("title") or ""
            text = rec.get("clean_text", "")
            meta = {
                "feed": rec.get("feed"),
                "country": rec.get("country"),
                "type": rec.get("type"),
                "license": rec.get("license"),
                "topics": rec.get("topics"),
                "tones": rec.get("tones"),
            }
            out = {
                "id": data.get("id") or data.get("link"),
                "source": rec.get("source"),
                "lang": rec.get("lang") or detect_lang(rec.get("country")),
                "title": title,
                "text": text,
                "meta": meta,
            }
            fout.write(json.dumps(out, ensure_ascii=False) + "\n")
    print(f"Zapisano: {OUT_PATH}")


if __name__ == "__main__":
    main()

