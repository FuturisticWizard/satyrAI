"""
Tworzy instrukcyjny dataset do treningu modelu SatyrAI.
Przekształca artykuły w pary prompt-response do supervised fine-tuning.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
IN_PATH = ROOT / "data" / "curated" / "tagged.jsonl"
OUT_PATH = ROOT / "data" / "curated" / "instruction_dataset.jsonl"

SATIRE_PROMPTS = [
    "Napisz satyryczny komentarz do następującego tematu:",
    "Stwórz ironiczny felieton o:",
    "Napisz humorystyczny tekst w stylu libertariańskim o:",
    "Skomentuj z dozą sarkazmu:",
    "Napisz satyrę polityczną na temat:",
]

COMMENTARY_PROMPTS = [
    "Napisz komentarz polityczny o:",
    "Przeanalizuj z perspektywy libertariańskiej:",
    "Napisz opinię o:",
    "Skomentuj następujący temat:",
    "Wyraź stanowisko w sprawie:",
]

def extract_key_phrases(text: str, max_phrases: int = 3) -> List[str]:
    """Wyciąga kluczowe frazy z tekstu jako basis dla promptu."""
    # Prosty extractor - w produkcji użyj NLP
    sentences = text.split('.')[:3]
    phrases = []
    for sent in sentences:
        words = sent.strip().split()
        if len(words) > 3:
            # Weź początek zdania jako kluczową frazę
            phrase = ' '.join(words[:6]) + "..."
            phrases.append(phrase)
    return phrases[:max_phrases]

def create_instruction(article: Dict[str, Any]) -> Dict[str, Any] | None:
    """Tworzy parę instruction-response z artykułu."""
    data = article.get('data', {})
    title = data.get('title', '').strip()
    
    # Spróbuj wyciągnąć pełną treść z content
    text = ""
    content_list = data.get('raw', {}).get('content', [])
    if content_list:
        # Weź pierwszy element content (HTML)
        html_content = content_list[0].get('value', '')
        # Prosta konwersja HTML na text (usuń tagi)
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').strip()
    
    # Fallback na clean_text jeśli content puste
    if not text:
        text = article.get('clean_text', '').strip()
    
    source = article.get('source', '')
    lang = article.get('lang', 'en')
    topics = article.get('topics', [])
    tone = article.get('tone', [])
    
    # Pomijaj zbyt krótkie teksty
    if len(text) < 100 or not title:
        return None
    
    # Wybierz typ promptu na podstawie tonu
    if 'satire' in tone:
        prompt_templates = SATIRE_PROMPTS
    else:
        prompt_templates = COMMENTARY_PROMPTS
    
    # Tylko polskie prompty na razie
    if lang == 'pl':
        # Użyj tytułu jako basis dla promptu
        base_prompt = random.choice(prompt_templates)
        instruction = f"{base_prompt} {title}"
    else:
        # Angielskie prompty - dodaj później
        base_prompt = "Write a libertarian commentary on:"
        instruction = f"{base_prompt} {title}"
    
    # Response to tekst artykułu
    response = text
    
    # Metadane do trackingu
    metadata = {
        'source': source,
        'language': lang,
        'topics': topics,
        'tone': tone,
        'original_id': article.get('data', {}).get('id')
    }
    
    return {
        'instruction': instruction,
        'response': response,
        'metadata': metadata
    }

def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    instructions = []
    skipped = 0
    
    with IN_PATH.open('r', encoding='utf-8') as fin:
        for line in fin:
            article = json.loads(line)
            instruction_pair = create_instruction(article)
            
            if instruction_pair:
                instructions.append(instruction_pair)
            else:
                skipped += 1
    
    # Zapisz jako JSONL
    with OUT_PATH.open('w', encoding='utf-8') as fout:
        for inst in instructions:
            fout.write(json.dumps(inst, ensure_ascii=False) + '\n')
    
    print(f"Utworzono {len(instructions)} par instruction-response")
    print(f"Pominięto {skipped} artykułów (zbyt krótkie)")
    print(f"Zapisano: {OUT_PATH}")
    
    # Pokaż przykład
    if instructions:
        sample = random.choice(instructions)
        print("\n--- Przykład pary instruction-response ---")
        print(f"INSTRUCTION: {sample['instruction']}")
        print(f"RESPONSE: {sample['response'][:200]}...")
        print(f"METADATA: {sample['metadata']}")

if __name__ == "__main__":
    main()