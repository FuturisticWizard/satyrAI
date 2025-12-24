"""
Test pojedynczego filmu z kanału Mentzena.
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "audio"
TRANSCRIPTS_DIR = ROOT / "data" / "youtube"

def download_and_transcribe_single_mentzen():
    """Pobiera i transkrybuje jeden film Mentzena."""
    
    # Najnowszy film Mentzena
    video_id = "2AjJtjXpZho"  # MENTZEN GRILLUJE #76
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    video_title = "MENTZEN GRILLUJE #76: Ziobro kontratakuje"
    
    print(f"🎯 Test: {video_title}")
    
    # Sprawdź czy już mamy
    transcript_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    if transcript_file.exists():
        print("✅ Transkrypcja już istnieje")
        return
    
    # Pobierz audio
    print("⬇️ Pobieranie audio...")
    audio_file = AUDIO_DIR / f"{video_id}.mp3"
    
    if not audio_file.exists():
        cmd = [
            "yt-dlp", "-x", "--audio-format", "mp3", 
            "--audio-quality", "0",
            "-o", str(AUDIO_DIR / "%(id)s.%(ext)s"),
            video_url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                print(f"❌ Błąd pobierania: {result.stderr}")
                return
        except subprocess.TimeoutExpired:
            print("❌ Timeout pobierania")
            return
    
    print(f"📊 Rozmiar audio: {audio_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Transkrybuj
    print("🎤 Transkrypcja...")
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_file), language="pl")
        
        # Zapisz
        transcript_data = {
            "video_id": video_id,
            "title": video_title,
            "url": video_url,
            "upload_date": "NA",
            "channel": "Sławomir Mentzen",
            "channel_key": "mentzen",
            "transcript": {
                "text": result["text"],
                "segments": result["segments"][:5],  # Pierwsze 5 segmentów
                "language": result["language"]
            },
            "processed_date": datetime.now().isoformat()
        }
        
        with transcript_file.open('w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Transkrypcja zapisana!")
        print(f"📖 Tekst ({len(result['text'])} znaków)")
        print(f"🔤 Pierwsze 200 znaków: {result['text'][:200]}...")
        
        # Usuń audio
        audio_file.unlink()
        print("🗑️ Audio usunięte")
        
        return transcript_data
        
    except Exception as e:
        print(f"❌ Błąd transkrypcji: {e}")
        return None

if __name__ == "__main__":
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🧪 TEST MENTZENA - POJEDYNCZY FILM\n")
    download_and_transcribe_single_mentzen()