"""
RSS fetcher (draft)
- Pobiera feedy z docs/whitelist.yaml
- Respektuje rate limit z config/config.yaml
- Zapisuje surowe wpisy do data/raw/{slug}.jsonl (per źródło) + zbiorczy rss_raw.jsonl
Uwaga: brak parsera licencji — należy użyć license_checker osobno.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import feedparser
import yaml

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "docs" / "whitelist.yaml"
CONFIG = ROOT / "config" / "config.yaml"
RAW_DIR = ROOT / "data" / "raw"


def load_config() -> Dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def load_whitelist() -> List[Dict[str, Any]]:
    return yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))


def rate_limit_sleep(rps: float) -> None:
    if rps <= 0:
        return
    time.sleep(1.0 / rps)


def fetch_feed(
    url: str, user_agent: Optional[str] = None, retries: int = 2
) -> Iterable[Dict[str, Any]]:
    headers = {"User-Agent": user_agent} if user_agent else None
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            parsed = feedparser.parse(url, request_headers=headers)
            for entry in parsed.entries:
                yield {
                    "id": entry.get("id") or entry.get("link"),
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "summary": entry.get("summary"),
                    "published": entry.get("published"),
                    "raw": entry,
                }
            return
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0)
                continue
            raise last_exc


def slugify(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def main(selected: Optional[str] = None) -> None:
    cfg = load_config()
    default_rps = cfg.get("rate_limit", {}).get("default_rps", 0.2)
    user_agent = cfg.get("fetch", {}).get("user_agent")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    whitelist = load_whitelist()
    out_path_all = RAW_DIR / "rss_raw.jsonl"
    with out_path_all.open("w", encoding="utf-8") as fall:
        for src in whitelist:
            name = src.get("name", "")
            if selected and selected.lower() not in name.lower():
                continue
            feed = src.get("feed")
            if not feed:
                continue
            rps = src.get("rate_limit_rps", default_rps)
            per_src = RAW_DIR / f"{slugify(name)}.jsonl"
            count = 0
            with per_src.open("w", encoding="utf-8") as fs:
                try:
                    for item in fetch_feed(feed, user_agent=user_agent):
                        record = {
                            "source": name,
                            "feed": feed,
                            "type": src.get("type"),
                            "country": src.get("country"),
                            "license": src.get("license"),
                            "data": item,
                        }
                        fs.write(json.dumps(record, ensure_ascii=False) + "\n")
                        fall.write(json.dumps(record, ensure_ascii=False) + "\n")
                        count += 1
                except Exception as exc:
                    print(f"[{name}] błąd pobierania ({exc}); pomijam ten feed")
            rate_limit_sleep(rps)
            print(f"[{name}] zapisano {count} wpisów -> {per_src}")
    print(f"Zapisano zbiorczo: {out_path_all}")


if __name__ == "__main__":
    main()
