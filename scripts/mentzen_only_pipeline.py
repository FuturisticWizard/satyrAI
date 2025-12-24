"""
Focused pipeline only for Mentzen channel transcriptions.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "audio"
TRANSCRIPTS_DIR = ROOT / "data" / "youtube"

# Mentzen channel
CHANNEL = {
    "url": "https://www.youtube.com/channel/UCkH8DpG5uKx0YsGCFWmOQcA",  
    "name": "Sławomir Mentzen",
    "recent_videos": 5  # Just 5 videos for testing
}

def get_recent_videos(channel_url, max_videos=5):
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
        for video in videos:
            print(f"  📹 {video['title']}")
        return videos
    
    except subprocess.TimeoutExpired:
        print("❌ Timeout przy pobieraniu listy")
        return []
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return []

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

def main():
    """Main function."""
    print("🚀 MENTZEN-ONLY TRANSCRIPTION PIPELINE\n")
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Pobierz listę filmów
    videos = get_recent_videos(CHANNEL['url'], CHANNEL['recent_videos'])
    if not videos:
        print("❌ Brak filmów do przetworzenia")
        return
    
    print(f"🎯 Będziemy przetwarzać WSZYSTKIE {len(videos)} filmów (bez filtrowania)")
    
    # 2. Pobierz audio i transkrybuj
    transcripts = []
    
    for i, video in enumerate(videos, 1):
        print(f"\n📹 [{i}/{len(videos)}] {video['title']}")
        
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
                "channel": CHANNEL['name'],
                "channel_key": "mentzen",
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
        
        print(f"  ⏱️  Postęp: {i}/{len(videos)}")
    
    print(f"\n✅ Gotowe: {len(transcripts)} nowych transkrypcji")
    
    if transcripts:
        print("\n📄 Pozyskane transkrypcje:")
        for t in transcripts:
            print(f"  - {t['title']} ({len(t['transcript']['text'])} znaków)")

if __name__ == "__main__":
    main()