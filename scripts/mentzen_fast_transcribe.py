"""
Szybka transkrypcja Mentzena z modelem 'tiny'.
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "audio"
TRANSCRIPTS_DIR = ROOT / "data" / "youtube"

def fast_transcribe():
    """Szybka transkrypcja z modelem tiny."""
    
    video_id = "2AjJtjXpZho" 
    audio_file = AUDIO_DIR / f"{video_id}.mp3"
    transcript_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    
    if not audio_file.exists():
        print("❌ Brak pliku audio")
        return
    
    if transcript_file.exists():
        print("✅ Transkrypcja już istnieje")
        return
    
    print(f"🎵 Plik: {audio_file}")
    print(f"📊 Rozmiar: {audio_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    try:
        import whisper
        print("🤖 Ładowanie modelu 'tiny' (najszybszy)...")
        model = whisper.load_model("tiny")
        
        print("🎤 Rozpoczynam szybką transkrypcję...")
        result = model.transcribe(str(audio_file), language="pl")
        
        transcript_data = {
            "video_id": video_id,
            "title": "MENTZEN GRILLUJE #76: Ziobro kontratakuje",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "upload_date": "NA",
            "channel": "Sławomir Mentzen",
            "channel_key": "mentzen",
            "transcript": {
                "text": result["text"],
                "segments": result["segments"][:3],  # Tylko 3 segmenty dla oszczędności
                "language": result["language"]
            },
            "processed_date": datetime.now().isoformat()
        }
        
        with transcript_file.open('w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Transkrypcja gotowa!")
        print(f"📄 Długość tekstu: {len(result['text'])} znaków")
        print(f"🔤 Fragment: {result['text'][:300]}...")
        
        return transcript_data
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return None

if __name__ == "__main__":
    print("⚡ SZYBKA TRANSKRYPCJA MENTZENA\n")
    fast_transcribe()