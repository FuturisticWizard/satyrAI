"""
Podział instruction datasetu na zbiory treningowy i ewaluacyjny.
Zachowuje stratyfikację po językach i źródłach.
"""
import json
import random
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "curated" / "instruction_dataset.jsonl"
TRAIN_PATH = ROOT / "data" / "curated" / "train_dataset.jsonl"
EVAL_PATH = ROOT / "data" / "curated" / "eval_dataset.jsonl"

EVAL_RATIO = 0.15  # 15% do ewaluacji
RANDOM_SEED = 42

def stratified_split(data: List[Dict[str, Any]], eval_ratio: float) -> tuple:
    """Stratyfikowany podział zachowujący proporcje języków i źródeł."""
    random.seed(RANDOM_SEED)
    
    # Grupuj po języku i źródle
    groups = defaultdict(list)
    for item in data:
        lang = item['metadata']['language']
        source = item['metadata']['source']
        key = f"{lang}_{source}"
        groups[key].append(item)
    
    train_data = []
    eval_data = []
    
    # Dla każdej grupy, zachowaj proporcję
    for group_key, group_items in groups.items():
        random.shuffle(group_items)
        eval_size = max(1, int(len(group_items) * eval_ratio))  # Min 1 na eval
        
        eval_items = group_items[:eval_size]
        train_items = group_items[eval_size:]
        
        eval_data.extend(eval_items)
        train_data.extend(train_items)
        
        print(f"Grupa {group_key}: {len(train_items)} train, {len(eval_items)} eval")
    
    # Tasuj końcowe zbiory
    random.shuffle(train_data)
    random.shuffle(eval_data)
    
    return train_data, eval_data

def main():
    """Główna funkcja podziału datasetu."""
    # Wczytaj dane
    print("Wczytywanie instruction dataset...")
    data = []
    with INPUT_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    
    print(f"Wczytano {len(data)} rekordów")
    
    # Stratyfikowany podział
    print(f"\nPodział na train/eval z ratio {EVAL_RATIO}")
    train_data, eval_data = stratified_split(data, EVAL_RATIO)
    
    # Zapisz zbiory
    print(f"\nZapis zbiorów...")
    TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with TRAIN_PATH.open('w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    with EVAL_PATH.open('w', encoding='utf-8') as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Podsumowanie
    print(f"\n=== PODSUMOWANIE ===")
    print(f"Train: {len(train_data)} przykładów -> {TRAIN_PATH}")
    print(f"Eval: {len(eval_data)} przykładów -> {EVAL_PATH}")
    print(f"Ratio eval: {len(eval_data)/len(data)*100:.1f}%")
    
    # Sprawdź dystrybucję języków
    train_langs = [item['metadata']['language'] for item in train_data]
    eval_langs = [item['metadata']['language'] for item in eval_data]
    
    from collections import Counter
    print(f"\nDystrybucja języków:")
    print(f"Train: {dict(Counter(train_langs))}")
    print(f"Eval: {dict(Counter(eval_langs))}")

if __name__ == "__main__":
    main()