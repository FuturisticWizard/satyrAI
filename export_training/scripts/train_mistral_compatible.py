#!/usr/bin/env python3
"""
Kompatybilna wersja treningu Mistral dla nowszych wersji TRL/Transformers
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer

# Konfiguracja
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "./results_mistral_rtx4090"

# Dane
if os.path.exists("export_training/data/train_dataset.jsonl"):
    train_file = "export_training/data/train_dataset.jsonl"
    val_file = "export_training/data/eval_dataset.jsonl"
else:
    raise FileNotFoundError("Nie znaleziono danych")

print(f"📁 Dane: {train_file}")

# Tokenizer
print("🔤 Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

# Format
def format_example(example):
    instruction = example["instruction"]
    response = example["response"]
    text = f"### Instruction:\n{instruction}\n### Response:\n{response}"
    return {"text": text}

# Dataset
print("📊 Dataset...")
dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})
dataset = dataset.map(format_example, remove_columns=dataset["train"].column_names)

print(f"Train: {len(dataset['train'])}, Val: {len(dataset['validation'])}")

# Model z quantization
print("🤖 Model...")
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
    use_cache=False,
)

# LoRA
print("🎯 LoRA...")
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Training args - kompatybilne z nowszą wersją
print("⚙️ Training args...")
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    logging_steps=10,
    learning_rate=2e-4,
    bf16=True,
    max_grad_norm=1.0,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    save_steps=500,
    eval_steps=500,
    eval_strategy="steps",  # Nowa nazwa
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",
    logging_first_step=True,
    remove_unused_columns=False,
)

# SFTTrainer - kompatybilna wersja
print("🎓 Trainer...")

# Sprawdź czy nowa czy stara wersja TRL
try:
    # Nowa wersja TRL
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        text_field="text",  # Nowa nazwa
        tokenizer=tokenizer,
        max_seq_length=2048,
        packing=False,
    )
except TypeError:
    # Stara wersja TRL
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        dataset_text_field="text",  # Stara nazwa
        tokenizer=tokenizer,
        max_seq_length=2048,
        packing=False,
    )

print("🚀 Trening...")
trainer.train()

print("💾 Zapisywanie...")
trainer.save_model(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("✅ Gotowe!")