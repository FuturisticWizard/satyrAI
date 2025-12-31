#!/usr/bin/env python3
"""
Skrypt treningu SatyrAI dla RTX 4090
Zoptymalizowany dla 24GB VRAM z 4-bit quantization i LoRA
"""

import os
import json
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer

# Konfiguracja dla RTX 4090
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "./results_rtx4090"

# Autowykrywanie danych
if os.path.exists("data/train_dataset.jsonl"):
    train_file = "data/train_dataset.jsonl"
    val_file = "data/eval_dataset.jsonl"
elif os.path.exists("export_training/data/train_dataset.jsonl"):
    train_file = "export_training/data/train_dataset.jsonl"
    val_file = "export_training/data/eval_dataset.jsonl"
elif os.path.exists("../data/train_dataset.jsonl"):
    train_file = "../data/train_dataset.jsonl"
    val_file = "../data/eval_dataset.jsonl"
else:
    raise FileNotFoundError("Nie znaleziono plików treningowych. Sprawdź czy dane są w data/ lub export_training/data/")

print(f"📁 Używam danych: {train_file}")

# Tokenizer
print("🔤 Ładowanie tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

# Format danych dla instruction tuning
def format_example(example):
    instruction = example["instruction"]
    response = example["response"]
    text = f"### Instruction:\n{instruction}\n### Response:\n{response}"
    return {"text": text}

# Załaduj dane
print("📊 Ładowanie danych...")
dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})
dataset = dataset.map(format_example, remove_columns=dataset["train"].column_names)

print(f"📈 Train samples: {len(dataset['train'])}")
print(f"📉 Val samples: {len(dataset['validation'])}")

# Model z quantization dla oszczędności VRAM na RTX 4090
print("🤖 Ładowanie modelu...")
print("⚙️  Używam 4-bit quantization dla RTX 4090...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    use_cache=False,  # Wymagane dla gradient checkpointing
)

# LoRA config - zoptymalizowane dla RTX 4090 (24GB VRAM)
print("🎯 Konfiguracja LoRA...")
lora_config = LoraConfig(
    r=16,                    # Rank - dobry kompromis jakość/szybkość
    lora_alpha=32,           # Alpha scaling
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",      # Attention layers
        "gate_proj", "up_proj", "down_proj"           # MLP layers
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Training arguments - RTX 4090 optimized
print("⚙️  Konfiguracja treningu dla RTX 4090...")
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,                      # 2 epoki to dobry start
    per_device_train_batch_size=4,           # RTX 4090 sweet spot
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,           # Effective batch size = 16
    gradient_checkpointing=True,             # Oszczędza VRAM
    optim="paged_adamw_8bit",               # Oszczędza memory
    logging_steps=10,
    learning_rate=2e-4,
    bf16=True,                              # RTX 4090 ma świetne wsparcie bf16
    max_grad_norm=1.0,
    warmup_ratio=0.05,                      # 5% kroków na warmup
    lr_scheduler_type="cosine",
    save_steps=500,
    eval_steps=500,
    eval_strategy="steps",
    save_total_limit=2,                     # Tylko 2 najlepsze checkpointy
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",                       # Bez wandb na początek
    logging_first_step=True,
    dataloader_pin_memory=False,            # Może pomóc z VRAM
)

# Trainer z SFT (Supervised Fine-Tuning)
print("🎓 Inicjalizacja trainer...")
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    dataset_text_field="text",
    tokenizer=tokenizer,
    max_seq_length=2048,                    # RTX 4090 może obsłużyć 2048 tokens
    packing=False,                          # Bez packingu dla prostoty
)

print("🚀 Rozpoczynam trening...")
print("💡 Monitoruj VRAM: watch -n 1 nvidia-smi")
print("-" * 50)

# Uruchom trening
trainer.train()

print("-" * 50)
print("💾 Zapisuję model...")
trainer.save_model(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("✅ Trening zakończony!")
print(f"📁 Model zapisany w: {OUTPUT_DIR}/final")
print(f"🎯 Aby przetestować model, uruchom:")
print(f"   python test_model_rtx4090.py")