"""
Test pojedynczego filmu YouTube - Stanowski.
"""
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "audio"  
OUTPUT_DIR = ROOT / "data" / "youtube"

# Test z konkretnym filmem Stanowskiego
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=StNmA41ag8Q"  # Ten co już pobraliśmy

def test_whisper_transcription():
    """Test transkrypcji z już pobranym plikiem."""
    
    # Sprawdź czy mamy plik audio
    audio_file = AUDIO_DIR / "StNmA41ag8Q.mp3"
    if not audio_file.exists():
        print("❌ Brak pliku audio - pobierz pierwszy")
        return
    
    print(f"🎵 Testowanie transkrypcji: {audio_file}")
    print(f"📊 Rozmiar pliku: {audio_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Użyj Whisper
    try:
        import whisper
        
        print("🤖 Ładowanie modelu Whisper...")
        model = whisper.load_model("base")
        
        print("🎤 Rozpoczynam transkrypcję...")
        result = model.transcribe(str(audio_file), language="pl")
        
        # Zapisz wynik
        transcript_data = {
            "video_id": "StNmA41ag8Q",
            "title": "MAZUREK: TUSK REDUCES GASOLINE PRICES. WE HAVE SUCCESS",
            "url": TEST_VIDEO_URL,
            "channel": "Kanał Zero",
            "transcript_text": result["text"],
            "segments": result["segments"][:5],  # Tylko pierwsze 5 segmentów dla testu
            "language": result["language"]
        }
        
        # Zapisz do pliku
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / "test_transcript.json"
        
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Transkrypcja zakończona!")
        print(f"📄 Tekst ({len(result['text'])} znaków):")
        print(f"📖 Pierwsze 300 znaków: {result['text'][:300]}...")
        print(f"💾 Zapisano do: {output_file}")
        
        return transcript_data
        
    except Exception as e:
        print(f"❌ Błąd transkrypcji: {e}")
        return None

def download_single_video():
    """Pobiera pojedynczy film jako test."""
    print(f"📺 Pobieranie testu: {TEST_VIDEO_URL}")
    
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3", 
        "--audio-quality", "0",
        "-o", str(AUDIO_DIR / "%(id)s.%(ext)s"),
        TEST_VIDEO_URL
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode == 0:
            print("✅ Audio pobrane")
            return True
        else:
            print(f"❌ Błąd pobierania: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

def main():
    """Test pipeline."""
    print("🧪 TEST POJEDYNCZEGO FILMU YOUTUBE\n")
    
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sprawdź czy mamy już audio
    audio_file = AUDIO_DIR / "StNmA41ag8Q.mp3"
    
    if audio_file.exists():
        print("✅ Audio już istnieje, przechodząc do transkrypcji")
    else:
        print("📥 Pobieranie audio...")
        if not download_single_video():
            return
    
    # Testuj transkrypcję
    transcript = test_whisper_transcription()
    
    if transcript:
        print(f"\n🎉 TEST ZAKOŃCZONY POMYŚLNIE!")
        print(f"📊 Pozyskano {len(transcript['transcript_text'])} znaków transkrypcji")
        
        # Pokaż fragment
        text = transcript['transcript_text']
        if len(text) > 100:
            print(f"\n--- FRAGMENT TRANSKRYPCJI ---")
            words = text.split()[:50]  # Pierwsze 50 słów  
            print(" ".join(words) + "...")
        else:
            print(f"❌ Transkrypcja za krótka: {text}")

if __name__ == "__main__":
    main()