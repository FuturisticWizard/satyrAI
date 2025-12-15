"""
Prosty tagger tematów i tonu (heurystyka słów kluczowych).
Wejście: data/clean/clean_lang.jsonl
Wyjście: data/curated/tagged.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "clean" / "clean_lang.jsonl"
OUT_PATH = ROOT / "data" / "curated" / "tagged.jsonl"

TOPIC_KEYWORDS = {
    "economics": ["inflacja", "podat", "gospodar", "econom", "market", "inflation", "tax"],
    "speech": ["cenzur", "wolność słowa", "free speech", "moderation"],
    "regulation": ["regulac", "ustaw", "directive", "regulation"],
    "foreign-policy": ["wojn", "nato", "ukrain", "rosj", "china", "geopolit"],
    "tech": ["internet", "big tech", "ai", "sztuczn", "privacy", "dane osobowe"],
}

TONE_KEYWORDS = {
    "satire": ["żart", "saty", "parodia", "ironi", "kpiar", "prześm"],
    "commentary": ["komentarz", "opinia", "analiza"],
}


def match_keywords(text: str, mapping: Dict[str, List[str]]) -> Set[str]:
    low = text.lower()
    tags: Set[str] = set()
    for tag, kws in mapping.items():
        if any(k in low for k in kws):
            tags.add(tag)
    return tags


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with IN_PATH.open("r", encoding="utf-8") as fin, OUT_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec: Dict[str, Any] = json.loads(line)
            text = rec.get("clean_text", "")
            topics = match_keywords(text, TOPIC_KEYWORDS)
            tones = match_keywords(text, TONE_KEYWORDS)
            rec["topics"] = sorted(topics)
            rec["tone"] = sorted(tones)[:1] if tones else []
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Zapisano: {OUT_PATH}")


if __name__ == "__main__":
    main()

