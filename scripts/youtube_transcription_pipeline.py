"""
Pipeline do pobierania i transkrypcji wideo z YouTube (Stanowski + Mentzen).
Używa yt-dlp + Whisper do tworzenia korpusu transkrypcji.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "audio"
TRANSCRIPTS_DIR = ROOT / "data" / "youtube"
MODELS_DIR = ROOT / "models"

# Kanały docelowe
CHANNELS = {
    "kanal_zero": {
        "url": "https://www.youtube.com/@KanalZeroPL",
        "name": "Kanał Zero (Stanowski)",
        "recent_videos": 15,  # Ostatnie 15 filmów
        "keywords": ["polityka", "wybory", "rząd", "opozycja", "komentarz", "tusk", "kaczyński"]
    },
    "mentzen": {
        "url": "https://www.youtube.com/channel/UCkH8DpG5uKx0YsGCFWmOQcA",  
        "name": "Sławomir Mentzen",
        "recent_videos": 10,  # Ostatnie 10 filmów
        "keywords": ["mentzen", "grilluje", "grills", "tusk", "pis", "konfederacja", "podatki", "taxes", "polish", "politicians"]
    }
}

def setup_directories():
    """Tworzy potrzebne katalogi."""
    for directory in [AUDIO_DIR, TRANSCRIPTS_DIR, MODELS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    print("✅ Katalogi przygotowane")

def check_dependencies():
    """Sprawdza czy mamy potrzebne narzędzia."""
    print("🔍 Sprawdzanie dependencies...")
    
    # yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        print("✅ yt-dlp dostępne")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Zainstaluj yt-dlp: pip install yt-dlp")
        return False
    
    # whisper
    try:
        import whisper
        print("✅ whisper dostępne")
    except ImportError:
        print("❌ Zainstaluj whisper: pip install openai-whisper")
        return False
    
    # ffmpeg (potrzebne dla whisper)
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ ffmpeg dostępne")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  ffmpeg może być potrzebne dla niektórych formatów")
    
    return True

def get_recent_videos(channel_url, max_videos=10):
    """Pobiera listę ostatnich filmów z kanału."""
    print(f"📺 Pobieranie listy filmów: {channel_url}")
    
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s|%(title)s|%(upload_date)s|%(duration)s",
        "--playlist-end", str(max_videos),
        f"{channel_url}/videos"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"❌ Błąd pobierania listy: {result.stderr}")
            return []
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    video_id, title, upload_date, duration = parts[:4]
                    videos.append({
                        'id': video_id,
                        'title': title,
                        'upload_date': upload_date,
                        'duration': duration,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    })
        
        print(f"✅ Znaleziono {len(videos)} filmów")
        return videos
    
    except subprocess.TimeoutExpired:
        print("❌ Timeout przy pobieraniu listy")
        return []
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return []

def filter_political_videos(videos, keywords):
    """Filtruje filmy zawierające słowa kluczowe polityczne."""
    filtered = []
    for video in videos:
        title_lower = video['title'].lower()
        if any(keyword in title_lower for keyword in keywords):
            filtered.append(video)
            print(f"  ✅ {video['title'][:60]}...")
        else:
            print(f"  ⏭️  Pomiń: {video['title'][:60]}...")
    
    return filtered

def download_audio(video_url, output_path):
    """Pobiera audio z YouTube w formacie MP3."""
    cmd = [
        "yt-dlp",
        "-x",  # Extract audio
        "--audio-format", "mp3",
        "--audio-quality", "0",  # Best quality
        "-o", str(output_path / "%(id)s.%(ext)s"),
        video_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)  # 5 min timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Timeout przy pobieraniu audio")
        return False
    except Exception as e:
        print(f"❌ Błąd pobierania: {e}")
        return False

def transcribe_audio(audio_path, model_size="base"):
    """Transkrybuje audio używając Whisper."""
    try:
        import whisper
        
        # Załaduj model (jeśli nie ma, pobierze automatycznie)
        print(f"🤖 Ładowanie modelu Whisper '{model_size}'...")
        model = whisper.load_model(model_size)
        
        print(f"🎵 Transkrypcja: {audio_path.name}")
        result = model.transcribe(str(audio_path), language="pl")
        
        return {
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"]
        }
    
    except Exception as e:
        print(f"❌ Błąd transkrypcji: {e}")
        return None

def process_channel(channel_key, channel_info):
    """Przetwarza jeden kanał - pobiera i transkrybuje."""
    print(f"\n🎬 === PRZETWARZANIE: {channel_info['name']} ===")
    
    # 1. Pobierz listę filmów
    videos = get_recent_videos(channel_info['url'], channel_info['recent_videos'])
    if not videos:
        print("❌ Brak filmów do przetworzenia")
        return
    
    # 2. Filtruj polityczne
    political_videos = filter_political_videos(videos, channel_info['keywords'])
    if not political_videos:
        print("❌ Brak filmów politycznych")
        return
    
    print(f"🎯 Wybrano {len(political_videos)} filmów do transkrypcji")
    
    # 3. Pobierz audio i transkrybuj
    transcripts = []
    
    for i, video in enumerate(political_videos[:5], 1):  # Limit 5 filmów na kanał
        print(f"\n📹 [{i}/{len(political_videos[:5])}] {video['title']}")
        
        # Sprawdź czy już mamy transkrypcję
        transcript_file = TRANSCRIPTS_DIR / f"{video['id']}.json"
        if transcript_file.exists():
            print("  ✅ Transkrypcja już istnieje")
            continue
        
        # Pobierz audio
        print("  ⬇️  Pobieranie audio...")
        audio_file = AUDIO_DIR / f"{video['id']}.mp3"
        
        if not audio_file.exists():
            if not download_audio(video['url'], AUDIO_DIR):
                print("  ❌ Błąd pobierania audio")
                continue
        
        # Transkrybuj
        print("  🎤 Transkrypcja...")
        transcript = transcribe_audio(audio_file, model_size="base")
        
        if transcript:
            # Zapisz transkrypcję z metadanymi
            full_transcript = {
                "video_id": video['id'],
                "title": video['title'],
                "url": video['url'],
                "upload_date": video['upload_date'],
                "channel": channel_info['name'],
                "channel_key": channel_key,
                "transcript": transcript,
                "processed_date": datetime.now().isoformat()
            }
            
            with transcript_file.open('w', encoding='utf-8') as f:
                json.dump(full_transcript, f, ensure_ascii=False, indent=2)
            
            transcripts.append(full_transcript)
            print("  ✅ Transkrypcja zapisana")
            
            # Usuń audio po transkrypcji (oszczędność miejsca)
            if audio_file.exists():
                audio_file.unlink()
                print("  🗑️  Audio usunięte")
        
        print(f"  ⏱️  Postęp: {i}/{len(political_videos[:5])}")
    
    print(f"\n✅ Kanał {channel_info['name']}: {len(transcripts)} transkrypcji")
    return transcripts

def export_for_training(channel_transcripts):
    """Eksportuje transkrypcje do formatu treningowego."""
    print("\n📤 Eksport do formatu treningowego...")
    
    training_data = []
    
    for channel_key, transcripts in channel_transcripts.items():
        for transcript in transcripts:
            # Podziel długie transkrypcje na segmenty
            text = transcript['transcript']['text']
            
            # Prosta segmentacja (można ulepszyć)
            sentences = text.split('. ')
            current_segment = ""
            
            for sentence in sentences:
                if len(current_segment + sentence) < 500:  # Max 500 znaków na segment
                    current_segment += sentence + ". "
                else:
                    if current_segment.strip():
                        training_data.append({
                            "source": transcript['channel'],
                            "feed": transcript['url'],
                            "type": "video_transcript", 
                            "country": "PL",
                            "license": "fair_use",
                            "data": {
                                "id": f"{transcript['video_id']}_seg_{len(training_data)}",
                                "title": transcript['title'],
                                "link": transcript['url'],
                                "summary": current_segment.strip(),
                                "published": transcript['upload_date'],
                                "raw": {
                                    "video_id": transcript['video_id'],
                                    "channel": transcript['channel_key'],
                                    "segment_text": current_segment.strip()
                                }
                            }
                        })
                    current_segment = sentence + ". "
            
            # Dodaj ostatni segment
            if current_segment.strip():
                training_data.append({
                    "source": transcript['channel'],
                    "feed": transcript['url'], 
                    "type": "video_transcript",
                    "country": "PL",
                    "license": "fair_use",
                    "data": {
                        "id": f"{transcript['video_id']}_seg_{len(training_data)}",
                        "title": transcript['title'],
                        "link": transcript['url'],
                        "summary": current_segment.strip(),
                        "published": transcript['upload_date'],
                        "raw": {
                            "video_id": transcript['video_id'],
                            "channel": transcript['channel_key'],
                            "segment_text": current_segment.strip()
                        }
                    }
                })
    
    # Zapisz w formacie JSONL
    output_file = ROOT / "data" / "raw" / "youtube_transcripts.jsonl"
    with output_file.open('w', encoding='utf-8') as f:
        for item in training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ Zapisano {len(training_data)} segmentów do {output_file}")
    return len(training_data)

def main():
    """Główna funkcja."""
    print("🚀 YOUTUBE TRANSCRIPTION PIPELINE")
    print("📺 Kanały: Stanowski (Kanał Zero) + Mentzen\n")
    
    setup_directories()
    
    if not check_dependencies():
        print("❌ Brakuje potrzebnych narzędzi")
        return
    
    all_transcripts = {}
    
    # Przetwarzaj każdy kanał
    for channel_key, channel_info in CHANNELS.items():
        transcripts = process_channel(channel_key, channel_info)
        if transcripts:
            all_transcripts[channel_key] = transcripts
    
    if all_transcripts:
        # Eksportuj do formatu treningowego
        total_segments = export_for_training(all_transcripts)
        
        print(f"\n🎉 PIPELINE ZAKOŃCZONY!")
        print(f"📊 Pozyskano {total_segments} segmentów treningowych")
        print(f"📁 Lokalizacja: {ROOT}/data/raw/youtube_transcripts.jsonl")
        print(f"🎯 Gotowe do włączenia do głównego korpusu!")
    else:
        print("\n❌ Nie udało się pozyskać żadnych transkrypcji")

if __name__ == "__main__":
    main()