# Szczegółowy przewodnik: trening testowy LLM (LoRA) na RunPod (RTX 5090 32 GB)

## Cel
Szybki proof-of-concept finetune modelu `mistralai/Mistral-7B-Instruct-v0.2` (styl satyry/prawicowo‑libertariański po polsku) na GPU RTX 5090 32 GB w RunPod. Dane wejściowe to `data/curated/training_candidates.jsonl` z istniejącego pipeline’u.

## 0. Start poda na RunPod (GUI)
1. Wybierz template z CUDA/PyTorch (np. oficjalny image RunPod „PyTorch”).  
2. Ustaw GPU: 1× RTX 5090 (32 GB), RAM 92 GB, dysk 80 GB.  
3. Uruchom poda, poczekaj aż będzie „running”, wejdź przez „Connect” → „SSH” lub WebTerminal.  
4. Zweryfikuj GPU:
   ```bash
   nvidia-smi
   ```
   Powinieneś widzieć 32 GB VRAM i sterownik CUDA.

## 1. Klon repo i środowisko
```bash
git clone <twoje-repo-satyrAI>.git
cd satyrAI
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install "torch>=2.3" transformers datasets accelerate peft bitsandbytes trl
```
> Jeśli pobieranie jest wolne, możesz dodać `-i https://pypi.org/simple`.

## 2. Odświeżenie danych (jeśli chcesz najnowszy zrzut)
```bash
source venv/bin/activate
python scripts/verify_feeds.py --update-robots
python ingest/rss_fetcher.py
python processing/clean_normalize.py
python processing/dedupe.py
python processing/pii_scrubber.py
python processing/toxicity_filter.py
python processing/lang_detect.py
python processing/tagger.py
python datasets/export_training_jsonl.py
python datasets/stats_report.py
```
Sprawdź `docs/stats_report.md` (liczność, kraje, typy).

## 3. Filtrowanie danych do treningu (PL, opinion/satire/economics)
```bash
python - <<'PY'
import json, random, pathlib
inp = pathlib.Path("data/curated/training_candidates.jsonl").read_text(encoding="utf-8").splitlines()
recs = [json.loads(x) for x in inp]
pl = [r for r in recs if r.get("lang") == "pl"]
keep_types = {"opinion", "satire", "economics"}
pl = [r for r in pl if r.get("type") in keep_types]
random.shuffle(pl)
split = int(0.9 * len(pl))
for name, subset in [("train", pl[:split]), ("val", pl[split:])]:
    pathlib.Path(f"data/curated/{name}.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in subset),
        encoding="utf-8",
    )
print("train", len(pl[:split]), "val", len(pl[split:]))
PY
```
Pliki wynikowe: `data/curated/train.jsonl`, `data/curated/val.jsonl`.

## 4. Skrypt treningowy `train_lora.py`
```python
import json
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

model_name = "mistralai/Mistral-7B-Instruct-v0.2"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token

train_file = "data/curated/train.jsonl"
val_file   = "data/curated/val.jsonl"

def format_example(ex):
    title = ex["data"].get("title", "")
    text  = ex.get("clean_text", "") or ex["data"].get("summary", "")
    prompt = (
        "### Polecenie:\n"
        f"Napisz satyryczny/prawicowo-libertariański komentarz po polsku na temat: {title}\n"
        "### Odpowiedź:\n"
        f"{text}"
    )
    return {"text": prompt}

ds = load_dataset("json", data_files={"train": train_file, "val": val_file})
ds = ds.map(format_example)

lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
)

model = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype="auto", device_map="auto"
)
model = get_peft_model(model, lora)

args = TrainingArguments(
    output_dir="out-lora",
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,  # eff. batch ~16
    learning_rate=2e-4,
    num_train_epochs=1,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    logging_steps=10,
    eval_steps=200,
    save_steps=500,
    evaluation_strategy="steps",
    bf16=True,
    save_total_limit=2,
    gradient_checkpointing=True,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=ds["train"],
    eval_dataset=ds["val"],
    dataset_text_field="text",
    max_seq_length=1024,
    args=args,
)

trainer.train()
trainer.save_model("out-lora/final")
```

## 5. Uruchomienie treningu
```bash
source venv/bin/activate
python train_lora.py
```
Logi pojawią się w konsoli; modele w `out-lora/`.

## 6. Inferencja z adapterem (test)
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

base = "mistralai/Mistral-7B-Instruct-v0.2"
adapter = "out-lora/final"
tokenizer = AutoTokenizer.from_pretrained(base, use_fast=True)
tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.float16, device_map="auto")
model = PeftModel.from_pretrained(model, adapter)

prompt = "### Polecenie:\nNapisz krótki, satyryczny komentarz o podatkach w Polsce w duchu libertariańskim.\n### Odpowiedź:\n"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
out = model.generate(**inputs, max_new_tokens=200, temperature=0.8, top_p=0.9)
print(tokenizer.decode(out[0], skip_special_tokens=True))
```

## 7. Regulacja zasobów i jakości
- Mniej VRAM: zmniejsz `max_seq_length` do 768/512 lub `r=8`.
- Lepsza jakość: 2–3 epoki (uważaj na overfitting – mało danych).
- Większy model (13B): użyj QLoRA 4-bit (bitsandbytes), ale będzie wolniej; na 32 GB powinno wejść.

## 8. Walidacja
- Eval loss/perplexity (wyniki z `eval_steps`).
- Ręczne próbki; opcjonalnie przepuść przez filtr toksyczności/PII (Detoxify/Perspective).

## 9. Szacunkowy czas/koszt na 5090
- LoRA 7B, 1 epoka, max_seq_length=1024, eff. batch ~16: zwykle kilkanaście–kilkadziesiąt minut.

## 10. Sprzątanie i eksport
- Pobierz `out-lora/final` (adaptery) na lokalny dysk (`scp`/`rsync`).
- Wyłącz/usuń poda po treningu, by zatrzymać koszty.


