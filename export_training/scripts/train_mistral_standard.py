#!/usr/bin/env python3
"""
Trening Mistral ze standardowym Trainer (bez SFTTrainer)
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    BitsAndBytesConfig,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType

# Konfiguracja
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OUTPUT_DIR = "./results_mistral_standard"

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
# Proper tokenizer setup for instruction training
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# Suppress tokenizer alignment warnings by ensuring token consistency
print("📋 Configuring tokenizer alignment...")

# Format i tokenizacja
def format_and_tokenize(example):
    instruction = example["instruction"]
    response = example["response"]
    text = f"### Instruction:\n{instruction}\n### Response:\n{response}{tokenizer.eos_token}"
    
    # Tokenizuj z padding=max_length dla stałej długości
    tokens = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=2048,
        return_tensors=None
    )
    
    # Dla causal LM, labels = input_ids
    tokens["labels"] = tokens["input_ids"].copy()
    
    # Zamień padding tokens w labels na -100 (ignorowane w loss)
    tokens["labels"] = [
        token_id if token_id != tokenizer.pad_token_id else -100
        for token_id in tokens["labels"]
    ]
    
    return tokens

# Dataset
print("📊 Ładowanie i tokenizacja...")
dataset = load_dataset("json", data_files={"train": train_file, "validation": val_file})
dataset = dataset.map(format_and_tokenize, remove_columns=dataset["train"].column_names)

print(f"Train: {len(dataset['train'])}, Val: {len(dataset['validation'])}")

# Model
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
    pad_token_id=tokenizer.pad_token_id,  # Align with tokenizer
)

# CRITICAL: Prepare model for k-bit training BEFORE applying LoRA
from peft.utils import prepare_model_for_kbit_training
model = prepare_model_for_kbit_training(model)

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

# Verify gradient configuration
trainable_params = [name for name, param in model.named_parameters() if param.requires_grad]
if trainable_params:
    print(f"✅ Trainable parameters found: {len(trainable_params)} layers")
else:
    print("❌ No trainable parameters! This will cause training failure.")
    # Emergency gradient enabling for LoRA layers
    for name, param in model.named_parameters():
        if 'lora' in name.lower():
            param.requires_grad = True
            print(f"Force enabled: {name}")

# Data collator - prosty dla pre-padded data
from transformers import default_data_collator
data_collator = default_data_collator  # Dla już sformatowanych danych

# Training arguments
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
    eval_strategy="steps",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",
    logging_first_step=True,
    dataloader_pin_memory=False,
)

# Standard Trainer
print("🎓 Trainer...")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    data_collator=data_collator,
    tokenizer=tokenizer,
)

print("🚀 Rozpoczynam trening...")
print("💡 Monitor: nvidia-smi")
print("-" * 50)

trainer.train()

print("-" * 50)
print("💾 Zapisywanie...")
trainer.save_model(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("✅ Mistral 7B trening zakończony!")
print(f"📁 Model: {OUTPUT_DIR}/final")