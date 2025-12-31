# SatyrAI - Instrukcje treningu na maszynie z GPU

## 1. Wymagania systemowe

### Hardware:
- **GPU**: RTX 4090/5090, A100, H100 (min 16GB VRAM)
- **RAM**: 32GB+ system memory
- **Storage**: 50GB+ wolnego miejsca

### Software:
- **CUDA**: 12.1+
- **Python**: 3.9-3.11
- **PyTorch**: 2.1+ with CUDA support

## 2. Setup środowiska i danych

### Opcja A: Sklonowanie z GitHub (zalecane dla programistów)
```bash
# Sklonuj repo
git clone https://github.com/your-username/satyrAI.git
cd satyrAI

# Stwórz środowisko
python -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Zainstaluj zależności
pip install -r requirements.txt
# LUB ręcznie:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets accelerate peft
pip install wandb tensorboard bitsandbytes
pip install huggingface_hub tokenizers

# Sprawdź CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name()}')"

# Przygotuj dane (jeśli repo nie ma gotowych danych treningowych)
cd export_training
# Dane są już w export_training/data/
```

### Opcja B: Użyj przygotowanego pakietu .tar.gz
```bash
# Wypakuj korpus
tar -xzf satyr_training_corpus_*.tar.gz
cd export_training  # lub satyr_training

# Stwórz środowisko
python -m venv venv
source venv/bin/activate

# Zainstaluj biblioteki (jak wyżej)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets accelerate peft
pip install wandb tensorboard bitsandbytes
pip install huggingface_hub tokenizers
```

## 3. Sprawdź dane treningowe

```bash
# Sprawdź dane (ścieżka zależy od opcji powyżej)
python -c "
import json
import os

# Dla opcji A (GitHub repo)
if os.path.exists('data/train_dataset.jsonl'):
    data_path = 'data'
# Dla opcji B (tar.gz)
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
except FileNotFoundError as e:
    print(f'❌ Błąd: {e}')
    print('Sprawdź czy jesteś w odpowiednim katalogu')
"
```

## 4. Alternatywnie: wygeneruj dane od nowa (dla opcji GitHub)

Jeśli sklonowałeś repo z GitHub i chcesz odświeżyć/przebudować dane treningowe:

```bash
# Upewnij się, że jesteś w głównym katalogu repo
cd satyrAI  # jeśli nie jesteś już tam

# Uruchom pipeline przetwarzania danych
python ingest/rss_fetcher.py
python processing/clean_normalize.py
python processing/dedupe.py
python processing/pii_scrubber.py
python processing/toxicity_filter.py
python processing/lang_detect.py
python processing/tagger.py

# Wygeneruj finalne pliki treningowe
python datasets/export_training_jsonl.py
python scripts/prepare_training_export.py

# Sprawdź statystyki
python datasets/stats_report.py
```

**Uwaga:** Ten krok jest opcjonalny jeśli repo już zawiera przygotowane dane w `export_training/data/`.

## 5. Modele do rozważenia

### Dla RTX 5090 (24GB):
- **Llama 3.1 8B** - najlepszy stosunek jakość/rozmiar
- **Mistral 7B v0.3** - szybki i stabilny
- **Llama 3.2 3B** - mały ale dobry

### Konfiguracja LoRA:
- **r=16, alpha=32** dla 7-8B modeli
- **r=8, alpha=16** dla oszczędzania VRAM
- **target_modules**: ["q_proj", "k_proj", "v_proj", "o_proj"]

## 6. Dostosowanie ścieżek w skryptach

Jeśli używasz opcji GitHub clone, może być potrzeba dostosowania ścieżek:

```python
# W skrypcie treningowym zmień ścieżki na odpowiednie:

# Dla opcji A (GitHub repo)
train_file = "export_training/data/train_dataset.jsonl"
val_file   = "export_training/data/eval_dataset.jsonl"

# Dla opcji B (tar.gz)  
train_file = "data/train_dataset.jsonl"
val_file   = "data/eval_dataset.jsonl"

# LUB użyj automatycznego wykrywania:
import os
if os.path.exists("export_training/data/train_dataset.jsonl"):
    data_dir = "export_training/data"
else:
    data_dir = "data"

train_file = f"{data_dir}/train_dataset.jsonl"
val_file   = f"{data_dir}/eval_dataset.jsonl"
```

## 7. Monitorowanie

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

---

# Co zrobić z wytrrenowanym modelem? - Przewodnik dla początkujących

## 8. Po zakończeniu treningu - masz wytrenowany model!

### Gdzie jest Twój model?
Po zakończeniu treningu znajdziesz swój model w folderze:
- `./results/` (lub `./out-lora/final` jeśli używałeś skryptu z docs/training_guide.md)
- Zawiera pliki: `adapter_config.json`, `adapter_model.safetensors`, `tokenizer.json`

### 8.1 Testowanie lokalnego modelu

```python
# test_model.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

# Załaduj model
base_model = "meta-llama/Llama-3.1-8B-Instruct"  # lub inny użyty
adapter_path = "./results"  # ścieżka do adaptera

tokenizer = AutoTokenizer.from_pretrained(base_model)
model = AutoModelForCausalLM.from_pretrained(
    base_model, 
    torch_dtype=torch.float16, 
    device_map="auto"
)
model = PeftModel.from_pretrained(model, adapter_path)

# Test
prompt = "Napisz satyryczny komentarz o inflacji w Polsce:"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=150)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### 8.2 Zapisywanie do Hugging Face Hub

```bash
# Zaloguj się do HF
pip install huggingface_hub
huggingface-cli login

# W Pythonie
from huggingface_hub import HfApi
api = HfApi()

# Stwórz repo (zamień 'twoja-nazwa' na swoją nazwę użytkownika)
api.create_repo("twoja-nazwa/satyr-ai-pl", private=True)

# Wgraj model
api.upload_folder(
    folder_path="./results",
    repo_id="twoja-nazwa/satyr-ai-pl",
    repo_type="model"
)
```

### 8.3 Używanie z zewnętrznych aplikacji

**Opcja 1: Lokalna aplikacja webowa**
```python
# app.py - prosty Flask serwer
from flask import Flask, request, jsonify
from transformers import pipeline

app = Flask(__name__)
generator = pipeline("text-generation", model="./results")

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json['prompt']
    result = generator(prompt, max_length=200)
    return jsonify({'text': result[0]['generated_text']})

if __name__ == '__main__':
    app.run(port=5000)
```

**Opcja 2: API przez Hugging Face Inference**
Po wgraniu na HF Hub, możesz używać przez API:
```python
import requests

API_URL = "https://api-inference.huggingface.co/models/twoja-nazwa/satyr-ai-pl"
headers = {"Authorization": f"Bearer {twój_token_hf}"}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

result = query({"inputs": "Napisz o podatkach:"})
print(result)
```

### 8.4 Integracja z popularnymi narzędziami

**Text Generation WebUI (Oobabooga)**
1. Pobierz: https://github.com/oobabooga/text-generation-webui
2. Skopiuj Twój model do `models/`
3. Uruchom WebUI i wybierz model z listy

**Ollama (dla łatwego deploymentu)**
1. Stwórz `Modelfile`:
```
FROM meta-llama/Llama-3.1-8B-Instruct
ADAPTER ./results
PARAMETER temperature 0.8
TEMPLATE "### Polecenie: {{.Prompt}}\n### Odpowiedź:"
```
2. `ollama create moj-satyr-model -f Modelfile`
3. `ollama run moj-satyr-model "Napisz o ekonomii"`

### 8.5 Optymalizacja dla produkcji

**Kwantyzacja (zmniejszenie rozmiaru)**
```python
# Użyj bitsandbytes dla 8-bit lub 4-bit
from transformers import BitsAndBytesConfig

config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    "ścieżka-do-modelu",
    quantization_config=config
)
```

**ONNX export dla szybkiej inferencji**
```python
# Konwersja do ONNX
from transformers import AutoModel
from transformers.onnx import export

model = AutoModel.from_pretrained("./results")
export(model, "model.onnx")
```

### 8.6 Monitorowanie i metryki

**Proste logowanie**
```python
import logging
from datetime import datetime

logging.basicConfig(
    filename='model_usage.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def generate_with_logging(prompt):
    start_time = datetime.now()
    result = model.generate(prompt)
    end_time = datetime.now()
    
    logging.info(f"Prompt: {prompt[:50]}... | "
                f"Time: {(end_time-start_time).total_seconds()}s")
    return result
```

## 9. Najczęstsze problemy dla początkujących

### "Out of memory" podczas inferencji
```python
# Użyj mniejszej precyzji
model = model.half()  # float16
# Lub kwantyzacji 8-bit
```

### Model generuje dziwne teksty
```python
# Dostosuj parametry generacji
outputs = model.generate(
    inputs,
    max_new_tokens=100,
    temperature=0.7,  # mniejsza = bardziej deterministyczne
    top_p=0.9,        # nucleus sampling
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id
)
```

### Chcę połączyć z ChatGPT/Claude API
```python
# wrapper.py - używaj swojego modelu jak ChatGPT API
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    messages = data['messages']
    
    # Skonwertuj na format Twojego modelu
    prompt = f"### Polecenie: {messages[-1]['content']}\n### Odpowiedź:"
    
    # Generuj odpowiedź
    response = your_model_generate(prompt)
    
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": response
            }
        }]
    }
```

## 10. Dystrybucja modelu

### Docker container
```dockerfile
# Dockerfile
FROM python:3.9-slim

RUN pip install torch transformers peft flask

COPY ./results /app/model
COPY app.py /app/

WORKDIR /app
EXPOSE 5000

CMD ["python", "app.py"]
```

### Udostępnianie publicznie
1. **Demo na Hugging Face Spaces** - stwórz `app.py` z Gradio/Streamlit
2. **GitHub Release** - spakuj model i wgraj jako release
3. **Model Cards** - napisz opis modelu na HF Hub

**Pamiętaj o licencjach!**
- Sprawdź licencję modelu bazowego
- Dodaj własną licencję do adaptera
- Dokumentuj źródła danych treningowych

---

Gratulacje! Masz własny wytrenowany model AI. Teraz możesz go używać, udoskonalać i dzielić się nim ze światem. 🎉
