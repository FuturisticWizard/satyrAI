"""
Przetwarza nowe dane przez pipeline czyszczenia i integruje z istniejącym korpusem.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
CURATED_DIR = ROOT / "data" / "curated"

def merge_new_data():
    """Merguje nowe pliki z istniejącymi raw data."""
    print("=== MERGING NOWYCH DANYCH ===\n")
    
    # Znajdź wszystkie nowe pliki (new- i phase2-)
    new_files = list(RAW_DIR.glob("new-*.jsonl")) + list(RAW_DIR.glob("phase2-*.jsonl"))
    print(f"Znaleziono {len(new_files)} nowych plików")
    
    total_merged = 0
    main_raw_file = RAW_DIR / "rss_raw.jsonl"
    
    # Otwórz główny plik w trybie append
    with main_raw_file.open('a', encoding='utf-8') as main_f:
        for new_file in new_files:
            print(f"Merging: {new_file.name}")
            
            count = 0
            with new_file.open('r', encoding='utf-8') as new_f:
                for line in new_f:
                    main_f.write(line)
                    count += 1
            
            total_merged += count
            print(f"  ✅ Dodano {count} artykułów")
            
            # Przenieś plik do archiwum
            archive_dir = RAW_DIR / "archive"
            archive_dir.mkdir(exist_ok=True)
            shutil.move(new_file, archive_dir / new_file.name)
    
    print(f"\nŁącznie dodano: {total_merged} artykułów")
    print(f"Pliki archiwalne: {archive_dir}")
    
    return total_merged

def run_processing_pipeline():
    """Uruchamia pipeline przetwarzania dla wszystkich danych."""
    print("\n=== URUCHAMIANIE PIPELINE PRZETWARZANIA ===\n")
    
    import subprocess
    import sys
    
    # Ustaw ścieżkę dla venv
    venv_python = ROOT / "venv" / "bin" / "python"
    
    # Kroki pipeline
    steps = [
        ("Normalizacja i czyszczenie", "processing/clean_normalize.py"),
        ("Deduplikacja", "processing/dedupe.py"), 
        ("Detekcja języka", "processing/lang_detect.py"),
        ("Filtr PII", "processing/pii_scrubber.py"),
        ("Filtr toksyczności", "processing/toxicity_filter.py"),
        ("Tagowanie", "processing/tagger.py")
    ]
    
    for step_name, script_path in steps:
        print(f"⚙️  {step_name}...")
        try:
            result = subprocess.run([
                str(venv_python), script_path
            ], 
            cwd=ROOT, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 min timeout
            )
            
            if result.returncode == 0:
                print(f"  ✅ {step_name} - OK")
                if result.stdout.strip():
                    print(f"  📄 {result.stdout.strip()}")
            else:
                print(f"  ❌ {step_name} - BŁĄD")
                print(f"  📄 {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {step_name} - TIMEOUT")
        except Exception as e:
            print(f"  ❌ {step_name} - {e}")
        
        print()
    
    print("Pipeline zakończony!")

def regenerate_training_data():
    """Regeneruje instruction dataset z nowymi danymi."""
    print("\n=== REGENERACJA INSTRUCTION DATASET ===\n")
    
    import subprocess
    
    venv_python = ROOT / "venv" / "bin" / "python"
    
    scripts = [
        ("Export training candidates", "datasets/export_training_jsonl.py"),
        ("Create instruction dataset", "datasets/create_instruction_dataset.py"),
        ("Train/eval split", "datasets/train_eval_split.py"),
        ("Stats report", "datasets/stats_report.py")
    ]
    
    for step_name, script_path in scripts:
        print(f"📊 {step_name}...")
        try:
            result = subprocess.run([
                str(venv_python), script_path
            ], 
            cwd=ROOT, 
            capture_output=True, 
            text=True
            )
            
            if result.returncode == 0:
                print(f"  ✅ OK")
                if result.stdout.strip():
                    # Pokaż tylko ostatnie linie output
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-3:]:
                        if line.strip():
                            print(f"  📄 {line}")
            else:
                print(f"  ❌ BŁĄD: {result.stderr}")
                
        except Exception as e:
            print(f"  ❌ {e}")
        
        print()

def main():
    """Główna funkcja przetwarzania."""
    print("🚀 ROZPOCZĘCIE PRZETWARZANIA FAZY 2\n")
    
    # 1. Merge nowych danych
    merged_count = merge_new_data()
    
    if merged_count == 0:
        print("Brak nowych danych do przetworzenia")
        return
    
    # 2. Pipeline przetwarzania  
    run_processing_pipeline()
    
    # 3. Regeneracja training data
    regenerate_training_data()
    
    print("\n🎉 PRZETWARZANIE FAZY 2 ZAKOŃCZONE!")
    print(f"Dodano {merged_count} nowych artykułów do korpusu")
    print("Corpus jest teraz gotowy do treningu modelu!")

if __name__ == "__main__":
    main()