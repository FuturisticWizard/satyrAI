"""
Pobiera najnowsze filmy z wybranych kanałów YouTube i zapisuje transkrypcje do data/youtube/.

Wymagania (venv):
    pip install yt-dlp youtube-transcript-api

Przykład:
    python scripts/youtube_fetch_and_transcribe.py --limit 5 --sleep 2

Domyślna lista kanałów pochodzi z docs/youtube_channels.md (ręcznie wklejona poniżej).
Skrypt:
1) Pobiera najnowsze ID z kanału (yt-dlp, tryb playlisty /videos).
2) Próbuje pobrać transkrypcję (YouTubeTranscriptApi) w jęz. pl, en (kolejność priorytetu).
3) Zapisuje JSONL per kanał w data/youtube/<channel_slug>.jsonl (append).

Uwaga: YouTube może nakładać limity (429). W razie problemów zwiększ --sleep lub zmniejsz --limit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

# Kanały: nazwa i URL do sekcji /videos
CHANNELS = [
    {"name": "Kto Wygrał", "url": "https://www.youtube.com/@KtoWygralOfficial/videos"},
    {
        "name": "Tomasz Wróblewski (WEI)",
        "url": "https://www.youtube.com/@TomaszWroblewskiWEI/videos",
    },
    {
        "name": "Warsaw Enterprise Institute",
        "url": "https://www.youtube.com/@WEIthink/videos",
    },
    {
        "name": "Nowa Konfederacja",
        "url": "https://www.youtube.com/@NowaKonfederacja/videos",
    },
    {
        "name": "Klub Jagielloński",
        "url": "https://www.youtube.com/@KlubJagiellonski/videos",
    },
    {"name": "DoRzeczy", "url": "https://www.youtube.com/@DoRzeczy/videos"},
    {"name": "wPolityce", "url": "https://www.youtube.com/@wpolitycepl/videos"},
    {"name": "NiezaleznaTV", "url": "https://www.youtube.com/@NiezaleznaPL/videos"},
    {"name": "Spiked", "url": "https://www.youtube.com/@SpikedOnlineVideo/videos"},
    {"name": "ReasonTV", "url": "https://www.youtube.com/@ReasonTV/videos"},
    {
        "name": "Cato Institute",
        "url": "https://www.youtube.com/@catoinstitutevideo/videos",
    },
    {"name": "Mises Institute", "url": "https://www.youtube.com/@misesmedia/videos"},
    {"name": "FEE", "url": "https://www.youtube.com/@FEEonline/videos"},
    {"name": "The Rubin Report", "url": "https://www.youtube.com/@RubinReport/videos"},
    {"name": "The Daily Wire", "url": "https://www.youtube.com/@DailyWire/videos"},
    {
        "name": "Valuetainment (PBD)",
        "url": "https://www.youtube.com/@Valuetainment/videos",
    },
    {
        "name": "Jordan B. Peterson",
        "url": "https://www.youtube.com/@JordanBPeterson/videos",
    },
    {"name": "John Stossel", "url": "https://www.youtube.com/@johnstossel/videos"},
]


def slugify(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def latest_video_ids(channel: dict, limit: int, timeout: int = 20) -> List[str]:
    """
    Pobiera najnowsze ID filmów z kanału używając yt-dlp w trybie playlisty /videos
    lub (gdy dostępne) z playlisty uploadów.
    Fallback: gdy /videos zwraca 404, używa wyszukiwarki ytsearch:<name> (ostatnie N).
    """
    channel_url = channel["url"]
    channel_name = channel.get("name", channel_url)

    # Spróbuj playlisty uploadów (bardziej stabilna niż /videos)
    uploads_url = resolve_uploads_playlist_url(
        channel_url, channel_name, timeout=timeout
    )
    primary_url = uploads_url or channel_url

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--get-id",
        "--playlist-end",
        str(limit),
        primary_url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        # Fallback: search
        search_query = f"ytsearch{limit}:{channel_name}"
        res = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--get-id", search_query],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed for {channel_url} and search '{search_query}': {res.stderr}"
            )

    ids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return ids[:limit]


def resolve_uploads_playlist_url(
    channel_url: str, channel_name: str, timeout: int = 20
) -> Optional[str]:
    """
    Próbuje wyznaczyć URL playlisty uploadów kanału (UU + channel_id bez 'UC').
    Zwraca None jeśli nie uda się pozyskać channel_id.
    """
    try:
        meta = subprocess.run(
            ["yt-dlp", "-j", channel_url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if meta.returncode != 0 or not meta.stdout:
            return None
        data = json.loads(meta.stdout.splitlines()[0])
        channel_id = data.get("channel_id")
        if channel_id and channel_id.startswith("UC") and len(channel_id) > 2:
            uploads_id = "UU" + channel_id[2:]
            return f"https://www.youtube.com/playlist?list={uploads_id}"
    except Exception:
        return None
    return None


def download_audio(
    video_id: str, target_dir: Path, timeout: int = 120
) -> Optional[Path]:
    """
    Pobiera audio z YouTube (bestaudio) do pliku w target_dir.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = target_dir / f"{video_id}.%(ext)s"
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio[ext=m4a]/bestaudio",
        "-o",
        str(out_template),
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        print(f"[{video_id}] yt-dlp audio fail: {res.stderr.strip()}")
        return None
    for ext in ("m4a", "webm", "opus", "mp3"):
        p = target_dir / f"{video_id}.{ext}"
        if p.exists():
            return p
    return None


def transcribe_with_whisper(
    audio_path: Path, model_name: str, language: Optional[str], device: Optional[str]
) -> Optional[str]:
    """
    Transkrybuje audio używając Whisper (wymaga pakietu `whisper` i ffmpeg).
    """
    try:
        import whisper  # type: ignore
    except Exception:
        return None
    try:
        model = whisper.load_model(model_name, device=device or "cpu")
        result = model.transcribe(
            str(audio_path),
            language=language,
            fp16=False if (device or "cpu") == "cpu" else True,
        )
        return result.get("text", "").strip()
    except Exception:
        print(f"[{audio_path.name}] whisper transcribe failed", file=sys.stderr)
        return None


def download_auto_caption(
    video_id: str, languages: List[str], target_dir: Path, timeout: int = 60
) -> Optional[str]:
    """
    Pobiera auto-napisy yt-dlp (vtt/srt) i zwraca tekst.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    for lang in languages:
        out_template = target_dir / f"{video_id}.{lang}.%(ext)s"
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang",
            lang,
            "--sub-format",
            "vtt/srt",
            "-o",
            str(out_template),
            url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode != 0:
            continue
        for ext in ("vtt", "srt"):
            p = target_dir / f"{video_id}.{lang}.{ext}"
            if p.exists():
                try:
                    text = parse_caption_file(p)
                    if text:
                        return text
                except Exception:
                    continue
    return None


def parse_caption_file(path: Path) -> str:
    """
    Proste parsowanie VTT/SRT: usuwa linie czasów, numery, tagi HTML.
    """
    import re

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: List[str] = []
    time_re = re.compile(r"^\d{1,2}:\d{2}:\d{2}")
    time_vtt_re = re.compile(r"^\d{2}:\d{2}\.\d{3}")
    for ln in lines:
        if not ln.strip():
            continue
        if ln.strip().isdigit():
            continue
        if "-->" in ln:
            continue
        if time_re.match(ln) or time_vtt_re.match(ln):
            continue
        clean = re.sub(r"<[^>]+>", "", ln).strip()
        if clean:
            out.append(clean)
    return " ".join(out).strip()


def fetch_metadata(video_id: str, timeout: int = 30) -> Optional[dict]:
    """
    Pobiera metadane jednego filmu (duration, upload_date) bez pobierania treści.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    res = subprocess.run(
        ["yt-dlp", "-j", "--skip-download", url],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if res.returncode != 0 or not res.stdout:
        return None
    try:
        data = json.loads(res.stdout.splitlines()[0])
        return {
            "duration": data.get("duration"),  # sekundy
            "upload_date": data.get("upload_date"),  # YYYYMMDD
        }
    except Exception:
        return None


def fetch_transcript(video_id: str, languages: List[str]) -> Optional[str]:
    """
    Próbuje pobrać transkrypt (manualny lub auto) w zadanych językach.
    """
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    except Exception:
        return None

    # manualne
    for lang in languages:
        try:
            data = transcripts.find_transcript([lang]).fetch()
            if data:
                return " ".join(
                    seg.get("text", "") for seg in data if seg.get("text")
                ).strip()
        except NoTranscriptFound:
            continue
        except Exception:
            continue

    # auto
    for lang in languages:
        try:
            data = transcripts.find_generated_transcript([lang]).fetch()
            if data:
                return " ".join(
                    seg.get("text", "") for seg in data if seg.get("text")
                ).strip()
        except NoTranscriptFound:
            continue
        except Exception:
            continue

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--limit", type=int, default=5, help="Ile najnowszych filmów na kanał"
    )
    ap.add_argument("--langs", default="pl,en", help="Priorytet języków, np. pl,en")
    ap.add_argument(
        "--sleep",
        type=float,
        default=1.5,
        help="Pauza (s) między requestami transkryptów",
    )
    ap.add_argument(
        "--channels",
        nargs="*",
        help="Opcjonalnie własna lista URL kanałów (zastępuje domyślną)",
    )
    ap.add_argument(
        "--output-dir", default="data/youtube", help="Folder wyjściowy na transkrypcje"
    )
    ap.add_argument(
        "--save-audio-dir",
        default=None,
        help="Jeśli podasz ścieżkę, zachowa pobrane audio w tym folderze (debug/archiwum)",
    )
    ap.add_argument(
        "--use-auto-captions",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pobieraj auto-napisy yt-dlp (vtt/srt) zanim uruchomisz Whisper",
    )
    ap.add_argument(
        "--whisper",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fallback: pobierz audio i transkrybuj Whisper, gdy brak napisów",
    )
    ap.add_argument(
        "--whisper-model",
        default="small",
        help="Model Whisper (tiny/base/small/medium/large...)",
    )
    ap.add_argument(
        "--whisper-device",
        default="cpu",
        help="Urządzenie dla Whisper (cpu/cuda/mps)",
    )
    ap.add_argument(
        "--max-duration",
        type=int,
        default=30,
        help="Pomiń filmy dłuższe niż X minut (filtr na metadanych, domyślnie 30)",
    )
    ap.add_argument(
        "--published-after",
        type=str,
        default=None,
        help="Pomiń filmy starsze niż data (YYYY-MM-DD)",
    )
    args = ap.parse_args()

    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    channels = CHANNELS
    if args.channels:
        channels = [{"name": url, "url": url} for url in args.channels]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    for ch in channels:
        name = ch["name"]
        url = ch["url"]
        slug = slugify(name or url)
        out_path = out_dir / f"{slug}.jsonl"
        try:
            ids = latest_video_ids(ch, args.limit)
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] błąd yt-dlp: {e}")
            continue

        written = 0
        with out_path.open("a", encoding="utf-8") as f:
            for vid in ids:
                # Filtry metadanych (długość, data)
                meta = fetch_metadata(vid)
                if meta:
                    duration = meta.get("duration")
                    upload_date = meta.get("upload_date")
                    if (
                        args.max_duration
                        and duration
                        and duration > args.max_duration * 60
                    ):
                        print(f"[{name}] skip {vid} (> {args.max_duration} min)")
                        continue
                    if args.published_after and upload_date:
                        try:
                            cutoff = datetime.fromisoformat(args.published_after).date()
                            up_date = datetime.strptime(upload_date, "%Y%m%d").date()
                            if up_date < cutoff:
                                print(
                                    f"[{name}] skip {vid} (upload {upload_date} < {cutoff})"
                                )
                                continue
                        except Exception:
                            pass

                text = fetch_transcript(vid, langs)
                if not text and args.use_auto_captions:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        text = download_auto_caption(vid, langs, Path(tmpdir))
                if not text and args.whisper:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        audio_path = download_audio(vid, Path(tmpdir))
                        if audio_path:
                            if args.save_audio_dir:
                                dest_dir = Path(args.save_audio_dir)
                                dest_dir.mkdir(parents=True, exist_ok=True)
                                shutil.copy(audio_path, dest_dir / audio_path.name)
                            whisper_lang = langs[0] if langs else None
                            text = transcribe_with_whisper(
                                audio_path,
                                args.whisper_model,
                                whisper_lang,
                                args.whisper_device,
                            )
                if not text:
                    time.sleep(args.sleep)
                    continue
                rec = {
                    "fetched_at": now,
                    "channel": name,
                    "channel_url": url,
                    "video_id": vid,
                    "lang_pref": langs,
                    "transcript": text,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
                time.sleep(args.sleep)
        print(f"[{name}] zapisano {written} transkryptów -> {out_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
