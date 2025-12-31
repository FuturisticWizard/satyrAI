#!/usr/bin/env python3

import json
import os

# Autowykrywanie ścieżki danych
if os.path.exists('data/train_dataset.jsonl'):
    data_path = 'data'
elif os.path.exists('export_training/data/train_dataset.jsonl'):
    data_path = 'export_training/data'
else:
    data_path = 'data'

try:
    with open(f'{data_path}/train_dataset.jsonl') as f:
        train_count = sum(1 for _ in f)
    with open(f'{data_path}/eval_dataset.jsonl') as f:
        eval_count = sum(1 for _ in f)
    print(f'✅ Dane znalezione w: {data_path}/')
    print(f'📊 Train samples: {train_count}')
    print(f'📊 Eval samples: {eval_count}')
    
    # Sprawdź przykładowy rekord treningowy
    with open(f'{data_path}/train_dataset.jsonl', 'r', encoding='utf-8') as f:
        sample = json.loads(f.readline())
        print(f'\n📋 Przykładowy rekord treningowy:')
        instruction = sample["instruction"][:100]
        response = sample["response"][:100]
        print(f'Instruction: {instruction}...')
        print(f'Response: {response}...')
        if 'metadata' in sample:
            metadata = sample['metadata']
            print(f'Source: {metadata.get("source", "N/A")}')
            print(f'Language: {metadata.get("language", "N/A")}')
            print(f'Topics: {metadata.get("topics", [])}')
        
    # Sprawdź rozkład języków
    languages = {}
    sources = {}
    with open(f'{data_path}/train_dataset.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            if 'metadata' in record:
                lang = record['metadata'].get('language', 'unknown')
                source = record['metadata'].get('source', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
                sources[source] = sources.get(source, 0) + 1
    
    print(f'\n🌍 Rozkład języków:')
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        print(f'  {lang}: {count} ({count/train_count*100:.1f}%)')
    
    print(f'\n📰 Top 5 źródeł:')
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f'  {source}: {count} ({count/train_count*100:.1f}%)')
        
except FileNotFoundError as e:
    print(f'❌ Błąd: {e}')
    print('Sprawdź czy jesteś w odpowiednim katalogu')
except json.JSONDecodeError as e:
    print(f'❌ Błąd parsowania JSON: {e}')
except Exception as e:
    print(f'❌ Nieoczekiwany błąd: {e}')