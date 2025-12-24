"""
Przygotowuje korpus treningowy do eksportu na maszynę z GPU.
Pakuje wszystkie niezbędne pliki i tworzy instrukcje setup.
"""
import json
import shutil
import tarfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "export_training"

def create_training_export():
    """Tworzy paczkę treningową do wysłania na maszynę z GPU."""
    print("🚀 PRZYGOTOWANIE KORPUSU DO EKSPORTU\n")
    
    # Wyczyść i stwórz katalog eksportu
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    EXPORT_DIR.mkdir(parents=True)
    
    print("📂 Kopiowanie plików treningowych...")
    
    # 1. Główne pliki treningowe
    training_files = {
        "train_dataset.jsonl": ROOT / "data" / "curated" / "train_dataset.jsonl",
        "eval_dataset.jsonl": ROOT / "data" / "curated" / "eval_dataset.jsonl", 
        "instruction_dataset.jsonl": ROOT / "data" / "curated" / "instruction_dataset.jsonl",
        "training_candidates.jsonl": ROOT / "data" / "curated" / "training_candidates.jsonl"
    }
    
    data_dir = EXPORT_DIR / "data"
    data_dir.mkdir()
    
    for filename, source_path in training_files.items():
        if source_path.exists():
            shutil.copy2(source_path, data_dir / filename)
            print(f"  ✅ {filename}")
        else:
            print(f"  ❌ Brak: {filename}")
    
    # 2. Konfiguracje i dokumentacja
    config_files = {
        "config.yaml": ROOT / "config" / "config.yaml",
        "whitelist.yaml": ROOT / "docs" / "whitelist.yaml",
        "stats_report.md": ROOT / "docs" / "stats_report.md",
        "data_training_plan.md": ROOT / "docs" / "data_training_plan.md"
    }
    
    config_dir = EXPORT_DIR / "config"
    config_dir.mkdir()
    
    for filename, source_path in config_files.items():
        if source_path.exists():
            shutil.copy2(source_path, config_dir / filename)
            print(f"  ✅ {filename}")
    
    # 3. Przykładowe skrypty treningowe
    scripts_dir = EXPORT_DIR / "scripts"
    scripts_dir.mkdir()
    
    # 4. Stwórz metadane eksportu
    metadata = {
        "export_date": datetime.now().isoformat(),
        "total_articles": get_dataset_size(data_dir / "instruction_dataset.jsonl"),
        "train_size": get_dataset_size(data_dir / "train_dataset.jsonl"),
        "eval_size": get_dataset_size(data_dir / "eval_dataset.jsonl"),
        "languages": get_language_distribution(data_dir / "train_dataset.jsonl"),
        "sources_count": get_sources_count(data_dir / "train_dataset.jsonl"),
        "recommended_models": [
            "microsoft/DialoGPT-medium", 
            "microsoft/DialoGPT-large",
            "meta-llama/Llama-3.2-3B-Instruct",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ],
        "hardware_requirements": {
            "gpu_memory": "16GB+ for 7B models, 24GB+ for 8B models",
            "system_ram": "32GB+", 
            "disk_space": "50GB+",
            "recommended_gpu": "RTX 4090/5090, A100, H100"
        }
    }
    
    with (EXPORT_DIR / "training_metadata.json").open('w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ training_metadata.json")
    
    # 5. Instrukcje setup
    create_setup_instructions(EXPORT_DIR)
    
    # 6. Przykładowy config treningu
    create_training_configs(EXPORT_DIR)
    
    # 7. Stwórz archiwum
    archive_path = ROOT / f"satyr_training_corpus_{datetime.now().strftime('%Y%m%d_%H%M')}.tar.gz"
    
    print(f"\n📦 Tworzenie archiwum: {archive_path}")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(EXPORT_DIR, arcname='satyr_training')
    
    # Podsumowanie
    archive_size = archive_path.stat().st_size / (1024 * 1024)  # MB
    
    print(f"\n🎉 EKSPORT GOTOWY!")
    print(f"📁 Archiwum: {archive_path}")
    print(f"📊 Rozmiar: {archive_size:.1f} MB")
    print(f"🎯 Gotowe do przesłania na maszynę z RTX 5090!")
    
    return archive_path

def get_dataset_size(file_path):
    """Zlicza linie w pliku JSONL."""
    if not file_path.exists():
        return 0
    with file_path.open('r') as f:
        return sum(1 for _ in f)

def get_language_distribution(file_path):
    """Pobiera dystrybucję języków."""
    if not file_path.exists():
        return {}
    
    langs = {}
    with file_path.open('r') as f:
        for line in f:
            data = json.loads(line)
            lang = data.get('metadata', {}).get('language', 'unknown')
            langs[lang] = langs.get(lang, 0) + 1
    return langs

def get_sources_count(file_path):
    """Zlicza unikalne źródła."""
    if not file_path.exists():
        return 0
    
    sources = set()
    with file_path.open('r') as f:
        for line in f:
            data = json.loads(line)
            source = data.get('metadata', {}).get('source', 'unknown')
            sources.add(source)
    return len(sources)

def create_setup_instructions(export_dir):
    """Tworzy instrukcje setup dla maszyny treningowej."""
    instructions = """# SatyrAI - Instrukcje treningu na maszynie z GPU

## 1. Wymagania systemowe

### Hardware:
- **GPU**: RTX 4090/5090, A100, H100 (min 16GB VRAM)
- **RAM**: 32GB+ system memory
- **Storage**: 50GB+ wolnego miejsca

### Software:
- **CUDA**: 12.1+
- **Python**: 3.9-3.11
- **PyTorch**: 2.1+ with CUDA support

## 2. Setup środowiska

```bash
# Zainstaluj wymagane biblioteki
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets accelerate peft
pip install wandb tensorboard bitsandbytes
pip install huggingface_hub tokenizers

# Sprawdź CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}')"
```

## 3. Załaduj dane

```bash
# Wypakuj korpus
tar -xzf satyr_training_corpus_*.tar.gz
cd satyr_training

# Sprawdź dane
python -c "
import json
with open('data/train_dataset.jsonl') as f:
    print(f'Train samples: {sum(1 for _ in f)}')
with open('data/eval_dataset.jsonl') as f:
    print(f'Eval samples: {sum(1 for _ in f)}')
"
```

## 4. Modele do rozważenia

### Dla RTX 5090 (24GB):
- **Llama 3.1 8B** - najlepszy stosunek jakość/rozmiar
- **Mistral 7B v0.3** - szybki i stabilny
- **Llama 3.2 3B** - mały ale dobry

### Konfiguracja LoRA:
- **r=16, alpha=32** dla 7-8B modeli
- **r=8, alpha=16** dla oszczędzania VRAM
- **target_modules**: ["q_proj", "k_proj", "v_proj", "o_proj"]

## 5. Monitorowanie

- Użyj **wandb** do trackingu metryk
- Sprawdzaj **GPU utilization** (nvidia-smi)
- **Eval loss** powinno spadać gładko
- **Perplexity** to główna metryka

## 6. Tips dla RTX 5090

- **Gradient checkpointing** = True (oszczędza VRAM)
- **Batch size**: 4-8 (dostosuj do VRAM)
- **Max length**: 2048 tokens
- **Learning rate**: 2e-4 (standard dla instruction tuning)
- **Warmup**: 0.05 (5% kroków)

## 7. Troubleshooting

- **OOM Error**: zmniejsz batch_size lub max_length
- **Slow training**: sprawdź czy używasz CUDA
- **Poor convergence**: sprawdź learning rate i warmup

Powodzenia z treningiem! 🚀
"""
    
    with (export_dir / "SETUP_INSTRUCTIONS.md").open('w', encoding='utf-8') as f:
        f.write(instructions)

def create_training_configs(export_dir):
    """Tworzy przykładowe konfiguracje treningu."""
    
    # Config dla Llama 3.1 8B
    llama_config = {
        "model_name": "meta-llama/Llama-3.1-8B-Instruct",
        "training_args": {
            "output_dir": "./results",
            "num_train_epochs": 3,
            "per_device_train_batch_size": 4,
            "per_device_eval_batch_size": 4,
            "gradient_accumulation_steps": 4,
            "gradient_checkpointing": True,
            "warmup_ratio": 0.05,
            "learning_rate": 2e-4,
            "fp16": True,
            "logging_steps": 50,
            "eval_steps": 500,
            "save_steps": 1000,
            "max_steps": 5000,
            "remove_unused_columns": False,
            "dataloader_pin_memory": False
        },
        "lora_config": {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "lora_dropout": 0.1,
            "bias": "none",
            "task_type": "CAUSAL_LM"
        }
    }
    
    # Config dla Mistral 7B
    mistral_config = {
        "model_name": "mistralai/Mistral-7B-Instruct-v0.3",
        "training_args": {
            "output_dir": "./results_mistral",
            "num_train_epochs": 3,
            "per_device_train_batch_size": 6,
            "per_device_eval_batch_size": 6,
            "gradient_accumulation_steps": 3,
            "gradient_checkpointing": True,
            "warmup_ratio": 0.05,
            "learning_rate": 2e-4,
            "fp16": True,
            "logging_steps": 50,
            "eval_steps": 500,
            "save_steps": 1000,
            "max_steps": 4000,
            "remove_unused_columns": False
        },
        "lora_config": {
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "lora_dropout": 0.1,
            "bias": "none",
            "task_type": "CAUSAL_LM"
        }
    }
    
    configs_dir = export_dir / "training_configs"
    configs_dir.mkdir()
    
    with (configs_dir / "llama_3_1_8b_config.json").open('w') as f:
        json.dump(llama_config, f, indent=2)
    
    with (configs_dir / "mistral_7b_config.json").open('w') as f:
        json.dump(mistral_config, f, indent=2)
    
    print(f"  ✅ training_configs/")

if __name__ == "__main__":
    create_training_export()