#!/usr/bin/env python3
"""
Trening Mistral bez quantization - dla pewności
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    Trainer,
    default_data_collator
)
from peft import LoraConfig, get_peft_model, TaskType

# Konfiguracja
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "./results_mistral_no_quant"

# Dane
if os.path.exists("export_training/data/train_dataset.jsonl"):
    train_file = "export_training/data/train_dataset.jsonl"
    val_file = "export_training/data/eval_dataset.jsonl"
else:
    raise FileNotFoundError("Brak danych")

print(f"📁 Dane: {train_file}")

# Tokenizer
print("🔤 Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

# Format i tokenizacja
def format_and_tokenize(example):
    instruction = example["instruction"]
    response = example["response"]
    text = f"### Instruction:\n{instruction}\n### Response:\n{response}{tokenizer.eos_token}"
    
    # Tokenizuj z padding=max_length
    tokens = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=1024,  # Mniej niż 2048 dla oszczędności VRAM
        return_tensors=None
    )
    
    # Labels = input_ids z -100 dla padding
    tokens["labels"] = [
        token_id if token_id != tokenizer.pad_token_id else -100
        for token_id in tokens["input_ids"]
    ]
    
    return tokens

# Dataset
print("📊 Ładowanie i tokenizacja...")
dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})
dataset = dataset.map(format_and_tokenize, remove_columns=dataset["train"].column_names)

print(f"Train: {len(dataset['train'])}, Val: {len(dataset['validation'])}")

# Model BEZ quantization - fp16
print("🤖 Model bez quantization...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,  # fp16 zamiast quantization
    device_map="auto",
    trust_remote_code=True,
    use_cache=False,
)

# LoRA
print("🎯 LoRA...")
lora_config = LoraConfig(
    r=8,  # Mniejszy rank dla oszczędności VRAM
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Mniej modułów
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Sprawdź gradienty
for name, param in model.named_parameters():
    if param.requires_grad:
        print(f"✅ Trainable: {name}")
        break

# Training arguments - mniejszy batch dla fp16
print("⚙️ Training args...")
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,
    per_device_train_batch_size=2,  # Mniejszy batch
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,  # Effective batch = 16
    gradient_checkpointing=True,
    optim="adamw_torch",
    logging_steps=10,
    learning_rate=2e-4,
    fp16=True,
    max_grad_norm=1.0,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    save_steps=500,
    eval_steps=500,
    eval_strategy="steps",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",
    logging_first_step=True,
    dataloader_pin_memory=False,
)

# Trainer
print("🎓 Trainer...")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    data_collator=default_data_collator,
)

print("🚀 Trening bez quantization...")
print("💡 Monitor VRAM: nvidia-smi")
print("-" * 50)

trainer.train()

print("-" * 50)
print("💾 Zapisywanie...")
trainer.save_model(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("✅ Mistral 7B (fp16) trening zakończony!")
print(f"📁 Model: {OUTPUT_DIR}/final")