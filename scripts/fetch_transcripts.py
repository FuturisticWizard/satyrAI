"""
Pobiera transkrypcje z filmów kanału YouTube (bez klucza API):
- Wyszukuje filmy z kanału po nazwie (yt-dlp).
- Dla każdego ID próbuje pobrać napisy (ręczne lub auto) przez youtube-transcript-api.
- Zapisuje transkrypcje do JSONL: jeden rekord na wideo.

Wymagania:
    pip install yt-dlp youtube-transcript-api

Przykład:
    python scripts/fetch_transcripts.py --channel "Kto Wygrał" --limit 50 --langs pl,en --output data/raw/transcripts_kw.jsonl
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def list_video_ids(channel: str, limit: int) -> List[str]:
    """Zwraca listę ID wideo z kanału, używając yt-dlp (tryb bez API)."""
    query = f"ytsearch{limit}:{channel}"
    cmd = ["yt-dlp", "--get-id", "--flat-playlist", query]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {res.stderr}")
    ids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return ids[:limit]


def fetch_transcript(
    video_id: str, languages: List[str], debug: bool = False
) -> str | None:
    """Pobiera transkrypt jako plain text. Próbujemy najpierw transkrypty ręczne, potem auto, wg listy lang."""
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    except Exception as e:  # noqa: BLE001
        if debug:
            print(f"[{video_id}] list_transcripts error: {e}")
        return None

    # Ręczne
    for lang in languages:
        try:
            data = transcripts.find_transcript([lang]).fetch()
            if data:
                return " ".join(
                    seg.get("text", "") for seg in data if seg.get("text")
                ).strip()
        except NoTranscriptFound:
            continue
        except Exception as e:  # noqa: BLE001
            if debug:
                print(f"[{video_id}] fetch manual {lang} error: {e}")
            continue

    # Auto-generated
    for lang in languages:
        try:
            data = transcripts.find_generated_transcript([lang]).fetch()
            if data:
                return " ".join(
                    seg.get("text", "") for seg in data if seg.get("text")
                ).strip()
        except NoTranscriptFound:
            continue
        except Exception as e:  # noqa: BLE001
            if debug:
                print(f"[{video_id}] fetch auto {lang} error: {e}")
            continue

    return None


def list_available_languages(video_id: str) -> List[str]:
    """Zwraca listę dostępnych kodów językowych (transkrypty i auto-transkrypty) dla video."""
    langs = []
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        langs.extend([tr.language_code for tr in transcripts])
        langs.extend([tr.language_code for tr in transcripts._generated_transcripts])
    except Exception:
        pass
    return sorted(set(langs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, help='Nazwa kanału, np. "Kto Wygrał"')
    ap.add_argument("--limit", type=int, default=50, help="Maksymalna liczba filmów")
    ap.add_argument("--langs", default="pl,en", help="Priorytet języków, np. pl,en")
    ap.add_argument(
        "--output", default="data/raw/transcripts.jsonl", help="Plik wyjściowy JSONL"
    )
    ap.add_argument(
        "--list-langs",
        action="store_true",
        help="Zamiast zapisywać transkrypty, wypisz dostępne języki dla filmów",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Wypisuj błędy pobierania transkryptów (debug)",
    )
    args = ap.parse_args()

    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    ids = list_video_ids(args.channel, args.limit)
    if args.list_langs:
        print(f"Znaleziono {len(ids)} ID wideo, wypisuję dostępne języki...")
        for vid in ids:
            avail = list_available_languages(vid)
            print(f"{vid}: {avail}")
        return

    print(f"Znaleziono {len(ids)} ID wideo, pobieram transkrypcje...")
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for vid in ids:
            text = fetch_transcript(vid, langs, debug=args.debug)
            if not text:
                continue
            rec = {
                "video_id": vid,
                "channel": args.channel,
                "lang_pref": langs,
                "transcript": text,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            print(f"OK {vid} (łącznie: {written})")

    print(f"Zapisano {written} transkryptów do {out_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
