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
import shlex
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


def parse_extra_yt_dlp_args(arg: Optional[str]) -> List[str]:
    """
    Parsuje dodatkowe argumenty dla yt-dlp (np. '--extractor-args "youtube:player_client=android"').
    """
    if not arg:
        return []
    try:
        return shlex.split(arg)
    except Exception:
        return arg.split()


def latest_video_ids(
    channel: dict,
    limit: int,
    timeout: int = 20,
    extra_yt_dlp_args: Optional[List[str]] = None,
) -> List[str]:
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

    extra = extra_yt_dlp_args or []
    
    # Prosta komenda dla pobierania ID
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--get-id",
        "--playlist-end",
        str(limit),
    ] + extra + [primary_url]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            ids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            # Filtruj nieprawidłowe ID (muszą mieć 11 znaków)
            valid_ids = [vid for vid in ids if len(vid) == 11 and vid.isalnum()]
            return valid_ids[:limit]
    except subprocess.TimeoutExpired:
        print(f"[{channel_name}] Timeout podczas pobierania listy filmów")
    except Exception as e:
        print(f"[{channel_name}] Błąd podczas pobierania listy filmów: {e}")

    # Fallback: search
    print(f"[{channel_name}] Próba fallback przez wyszukiwanie...")
    try:
        search_query = f"ytsearch{limit}:{channel_name}"
        search_cmd = [
            "yt-dlp",
            "--flat-playlist", 
            "--get-id",
            search_query
        ]
        res = subprocess.run(
            search_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0:
            ids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            valid_ids = [vid for vid in ids if len(vid) == 11 and vid.isalnum()]
            return valid_ids[:limit]
        else:
            print(f"[{channel_name}] Search fallback failed: {res.stderr.strip()}")
    except Exception as e:
        print(f"[{channel_name}] Search fallback error: {e}")
    
    raise RuntimeError(f"Nie udało się pobrać filmów z kanału {channel_name} ({channel_url})")


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
    video_id: str,
    target_dir: Path,
    timeout: int = 120,
    extra_yt_dlp_args: Optional[List[str]] = None,
    max_retries: int = 3,
) -> Optional[Path]:
    """
    Pobiera audio z YouTube (bestaudio) do pliku w target_dir z retry logic.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    out_template = target_dir / f"{video_id}.%(ext)s"
    url = f"https://www.youtube.com/watch?v={video_id}"
    extra = extra_yt_dlp_args or []
    
    # Prosta komenda bez dodatkowych argumentów - jak w działającym przykładzie
    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio",
        "-o",
        str(out_template),
    ] + extra + [url]
    
    for attempt in range(max_retries):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode == 0:
                # Sprawdź czy plik został utworzony (priorytet dla popularnych formatów audio)
                for ext in ("mp3", "m4a", "webm", "opus", "mp4"):
                    p = target_dir / f"{video_id}.{ext}"
                    if p.exists():
                        return p
                print(f"[{video_id}] Warning: yt-dlp succeeded but no output file found")
                return None
            else:
                stderr = res.stderr.strip()
                if "403" in stderr or "Forbidden" in stderr:
                    print(f"[{video_id}] 403 Forbidden - video may be restricted")
                    return None
                elif "unavailable" in stderr.lower() or "private" in stderr.lower():
                    print(f"[{video_id}] Video unavailable or private")
                    return None
                elif attempt < max_retries - 1:
                    print(f"[{video_id}] Attempt {attempt + 1} failed, retrying... ({stderr[:100]})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"[{video_id}] yt-dlp audio fail after {max_retries} attempts: {stderr}")
                    return None
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                print(f"[{video_id}] Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2 ** attempt)
            else:
                print(f"[{video_id}] Timeout after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[{video_id}] Error on attempt {attempt + 1}: {e}, retrying...")
                time.sleep(2 ** attempt)
            else:
                print(f"[{video_id}] Error after {max_retries} attempts: {e}")
                return None
    
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
    video_id: str,
    languages: List[str],
    target_dir: Path,
    timeout: int = 60,
    extra_yt_dlp_args: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Pobiera auto-napisy yt-dlp (vtt/srt) i zwraca tekst.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    extra = extra_yt_dlp_args or []
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
            *extra,
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


def fetch_metadata(
    video_id: str, timeout: int = 30, extra_yt_dlp_args: Optional[List[str]] = None
) -> Optional[dict]:
    """
    Pobiera metadane jednego filmu (duration, upload_date) bez pobierania treści.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    extra = extra_yt_dlp_args or []
    res = subprocess.run(
        ["yt-dlp", "-j", "--skip-download", *extra, url],
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
    ap.add_argument(
        "--yt-dlp-args",
        default=None,
        help='Dodatkowe argumenty dla yt-dlp (np. --extractor-args "youtube:player_client=android")',
    )
    ap.add_argument(
        "--simple-whisper-only",
        action="store_true",
        help="Tryb diagnostyczny: pobierz audio i transkrybuj Whisper, bez napisów/auto-napisów",
    )
    args = ap.parse_args()

    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    extra_args = parse_extra_yt_dlp_args(args.yt_dlp_args)
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
            ids = latest_video_ids(ch, args.limit, extra_yt_dlp_args=extra_args)
            print(f"[{name}] znaleziono {len(ids)} filmów")
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] błąd pobierania listy filmów: {e}")
            continue

        written = 0
        print(f"[{name}] rozpoczynam przetwarzanie {len(ids)} filmów...")
        with out_path.open("a", encoding="utf-8") as f:
            for i, vid in enumerate(ids, 1):
                print(f"[{name}] przetwarzam film {i}/{len(ids)}: {vid}")
                text = None

                # Filtry metadanych (długość, data) jeśli nie tryb prosty
                if not args.simple_whisper_only:
                    print(f"[{name}] {vid}: pobieranie metadanych...")
                    meta = fetch_metadata(vid, extra_yt_dlp_args=extra_args)
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
                                cutoff = datetime.fromisoformat(
                                    args.published_after
                                ).date()
                                up_date = datetime.strptime(
                                    upload_date, "%Y%m%d"
                                ).date()
                                if up_date < cutoff:
                                    print(
                                        f"[{name}] skip {vid} (upload {upload_date} < {cutoff})"
                                    )
                                    continue
                            except Exception:
                                pass

                    print(f"[{name}] {vid}: szukam transkrypcji YouTube API...")
                    text = fetch_transcript(vid, langs)
                    if text:
                        print(f"[{name}] {vid}: znaleziono transkrypcję z YouTube API (długość: {len(text)} znaków)")
                    else:
                        print(f"[{name}] {vid}: brak transkrypcji z YouTube API")
                    if not text and args.use_auto_captions:
                        print(f"[{name}] {vid}: próba pobrania auto-napisów...")
                        with tempfile.TemporaryDirectory() as tmpdir:
                            text = download_auto_caption(
                                vid, langs, Path(tmpdir), extra_yt_dlp_args=extra_args
                            )
                        if text:
                            print(f"[{name}] {vid}: znaleziono auto-napisy (długość: {len(text)} znaków)")
                        else:
                            print(f"[{name}] {vid}: brak auto-napisów")

                # Whisper (fallback lub tryb prosty)
                if (not text and args.whisper) or args.simple_whisper_only:
                    print(f"[{name}] {vid}: rozpoczynam pobieranie audio dla Whisper...")
                    with tempfile.TemporaryDirectory() as tmpdir:
                        audio_path = download_audio(
                            vid, Path(tmpdir), extra_yt_dlp_args=extra_args, max_retries=3
                        )
                        if audio_path:
                            print(f"[{name}] {vid}: pobrano audio {audio_path.name}, rozpoczynam transkrypcję Whisper...")
                            if args.save_audio_dir:
                                dest_dir = Path(args.save_audio_dir)
                                dest_dir.mkdir(parents=True, exist_ok=True)
                                shutil.copy(audio_path, dest_dir / audio_path.name)
                                print(f"[{name}] {vid}: zapisano audio do {dest_dir / audio_path.name}")
                            whisper_lang = langs[0] if langs else None
                            text = transcribe_with_whisper(
                                audio_path,
                                args.whisper_model,
                                whisper_lang,
                                args.whisper_device,
                            )
                            if text:
                                print(f"[{name}] {vid}: transkrypcja Whisper zakończona (długość: {len(text)} znaków)")
                            else:
                                print(f"[{name}] {vid}: transkrypcja Whisper nie powiodła się")
                        else:
                            print(f"[{name}] {vid}: nie udało się pobrać audio")
                if not text:
                    print(f"[{name}] {vid}: brak tekstu - pomijam")
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
                print(f"[{name}] {vid}: zapisano transkrypcję (łącznie: {written}/{len(ids)})")
                time.sleep(args.sleep)
        print(f"[{name}] zapisano {written} transkryptów -> {out_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
