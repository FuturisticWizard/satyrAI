"""
Analiza jakości instruction datasetu.
"""
import json
from pathlib import Path
from collections import Counter
import statistics

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "curated" / "instruction_dataset.jsonl"

def analyze_dataset():
    """Analizuje instruction dataset pod kątem jakości i dystrybucji."""
    
    instructions = []
    responses = []
    languages = []
    sources = []
    
    with DATASET_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            instructions.append(data['instruction'])
            responses.append(data['response'])
            languages.append(data['metadata']['language'])
            sources.append(data['metadata']['source'])
    
    print("=== ANALIZA INSTRUCTION DATASET ===\n")
    
    # Podstawowe statystyki
    print(f"Całkowita liczba par: {len(instructions)}")
    print(f"Języki: {dict(Counter(languages))}")
    print(f"Najczęstsze źródła: {dict(Counter(sources).most_common(5))}")
    
    # Długość tekstów
    instruction_lengths = [len(inst) for inst in instructions]
    response_lengths = [len(resp) for resp in responses]
    
    print(f"\nDługość instrukcji:")
    print(f"  Średnia: {statistics.mean(instruction_lengths):.1f} znaków")
    print(f"  Mediana: {statistics.median(instruction_lengths):.1f} znaków")
    print(f"  Min/Max: {min(instruction_lengths)}/{max(instruction_lengths)}")
    
    print(f"\nDługość odpowiedzi:")
    print(f"  Średnia: {statistics.mean(response_lengths):.1f} znaków")
    print(f"  Mediana: {statistics.median(response_lengths):.1f} znaków")
    print(f"  Min/Max: {min(response_lengths)}/{max(response_lengths)}")
    
    # Przykłady
    print(f"\n=== PRZYKŁADY ===")
    sample_indices = [0, len(instructions)//2, -1]
    for i, idx in enumerate(sample_indices):
        print(f"\n--- Przykład {i+1} ---")
        print(f"INSTRUKCJA: {instructions[idx]}")
        print(f"ODPOWIEDŹ: {responses[idx][:200]}...")
        print(f"JĘZYK: {languages[idx]} | ŹRÓDŁO: {sources[idx]}")
    
    # Potencjalne problemy
    print(f"\n=== POTENCJALNE PROBLEMY ===")
    
    short_responses = sum(1 for r in response_lengths if r < 500)
    print(f"Krótkie odpowiedzi (<500 znaków): {short_responses} ({short_responses/len(responses)*100:.1f}%)")
    
    long_responses = sum(1 for r in response_lengths if r > 4000)
    print(f"Bardzo długie odpowiedzi (>4000 znaków): {long_responses} ({long_responses/len(responses)*100:.1f}%)")
    
    # Duplikaty instrukcji
    unique_instructions = len(set(instructions))
    print(f"Unikalne instrukcje: {unique_instructions}/{len(instructions)} ({unique_instructions/len(instructions)*100:.1f}%)")

if __name__ == "__main__":
    analyze_dataset()