#!/usr/bin/env python3
"""
Test wytrenowanego modelu SatyrAI na RTX 4090
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import warnings
warnings.filterwarnings("ignore")

# Konfiguracja
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER_PATH = "./results_rtx4090/final"

def test_model():
    print("🔄 Ładowanie modelu...")
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Base model
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, 
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Załaduj adapter LoRA
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    
    print("✅ Model załadowany!")
    print(f"🎯 GPU: {torch.cuda.get_device_name()}")
    print(f"💾 VRAM: {torch.cuda.memory_allocated() / 1024**3:.1f}GB")
    
    # Testy
    test_prompts = [
        "Napisz krótki satyryczny komentarz o inflacji w Polsce",
        "Skomentuj z perspektywy libertariańskiej: wzrost podatków",
        "Write a libertarian opinion about government spending",
        "Opisz ironicznie biurokrację urzędniczą",
        "Comment on free market economics"
    ]
    
    print("\n🎭 Testowanie modelu:")
    print("=" * 60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[Test {i}/5]")
        print(f"Prompt: {prompt}")
        print("-" * 40)
        
        # Format instruction
        full_prompt = f"### Instruction:\n{prompt}\n### Response:\n"
        
        # Tokenize
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.8,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode response
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the model's response (after "### Response:")
        if "### Response:\n" in full_response:
            response = full_response.split("### Response:\n")[1].strip()
        else:
            response = full_response[len(full_prompt):].strip()
        
        print(f"Response: {response}")
        print()

def quick_test():
    """Szybki test czy model się ładuje"""
    try:
        print("⚡ Szybki test ładowania...")
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        
        # Test czy adapter istnieje
        import os
        if not os.path.exists(ADAPTER_PATH):
            print(f"❌ Nie znaleziono adaptera w: {ADAPTER_PATH}")
            print("💡 Najpierw uruchom trening: python train_llama_rtx4090.py")
            return False
            
        print(f"✅ Adapter znaleziony: {ADAPTER_PATH}")
        
        # Check required files
        required_files = ["adapter_config.json", "adapter_model.safetensors"]
        for file in required_files:
            if os.path.exists(os.path.join(ADAPTER_PATH, file)):
                print(f"✅ {file}")
            else:
                print(f"❌ Brak pliku: {file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

if __name__ == "__main__":
    print("🎯 SatyrAI Model Tester - RTX 4090")
    print("=" * 50)
    
    if quick_test():
        print("\n🚀 Uruchamiam pełny test...")
        test_model()
        print("\n🎉 Test zakończony!")
    else:
        print("\n❌ Test nie może być uruchomiony")