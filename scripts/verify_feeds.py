"""
Półautomatyczna weryfikacja feedów z docs/whitelist.yaml:
- Sprawdza robots.txt (czy feed jest dozwolony dla default user-agent).
- Wysyła HEAD do feeda (fallback GET) by sprawdzić status/redirect.
- Generuje raport markdown (docs/verification_report.md).
- Opcjonalnie może zaktualizować pole robots_ok w whitelist.yaml.
Uwaga: licencji nie da się automatycznie potwierdzić — pozostaje ręczna inspekcja Terms/FAQ.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = ROOT / "docs" / "whitelist.yaml"
REPORT = ROOT / "docs" / "verification_report.md"


def load_whitelist() -> List[Dict[str, Any]]:
    data = yaml.safe_load(WHITELIST.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("whitelist.yaml musi zawierać listę obiektów")
    return data


def check_robots(feed_url: str, user_agent: str = "*") -> Tuple[bool, str]:
    parsed = urlparse(feed_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(user_agent, feed_url)
        return allowed, robots_url
    except Exception:
        return False, robots_url


def head_feed(feed_url: str, timeout: float = 5.0) -> Tuple[int, str]:
    try:
        resp = requests.head(feed_url, timeout=timeout, allow_redirects=True)
        return resp.status_code, resp.url
    except requests.RequestException:
        try:
            resp = requests.get(feed_url, timeout=timeout, allow_redirects=True)
            return resp.status_code, resp.url
        except requests.RequestException:
            return 0, feed_url


def build_report(entries: List[Dict[str, Any]]) -> str:
    lines = [
        "# Verification report (feed/robots)",
        "",
        "| name | feed | status | final_url | robots_allowed | robots_txt | notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for e in entries:
        lines.append(
            f"| {e.get('name','')} | {e.get('feed','')} | {e.get('http_status','')} "
            f"| {e.get('final_url','')} | {e.get('robots_allowed','')} "
            f"| {e.get('robots_url','')} | {e.get('notes','')} |"
        )
    lines.append("")
    lines.append("> Licencje: do ręcznej weryfikacji w Terms/FAQ każdej strony.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-robots", action="store_true", help="Aktualizuj robots_ok na podstawie sprawdzenia")
    parser.add_argument("--user-agent", default="*", help="User-Agent dla robots.txt")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout dla zapytań HTTP")
    args = parser.parse_args()

    entries = load_whitelist()
    results = []
    for entry in entries:
        feed = entry.get("feed")
        if not feed:
            continue
        robots_allowed, robots_url = check_robots(feed, user_agent=args.user_agent)
        status_code, final_url = head_feed(feed, timeout=args.timeout)

        entry["robots_allowed"] = robots_allowed
        entry["robots_url"] = robots_url
        entry["http_status"] = status_code
        entry["final_url"] = final_url

        if args.update_robots:
            entry["robots_ok"] = bool(robots_allowed)

        results.append(entry)

    report = build_report(results)
    REPORT.write_text(report, encoding="utf-8")

    if args.update_robots:
        WHITELIST.write_text(yaml.safe_dump(entries, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"Zapisano raport: {REPORT}")
    if args.update_robots:
        print(f"Zaktualizowano: {WHITELIST}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        sys.exit(1)

