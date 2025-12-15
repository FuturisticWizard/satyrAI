# Developer Guide — SatyrAI (Python pipelines)

## Zakres
Instrukcje dla developerów budujących pipeline ingest/clean/tag/train oraz serwisy guardrails/inference dla portalu satyryczno‑politycznego.

## Struktura katalogów (propozycja)
- `ingest/` — pobieranie feedów/crawling, licencje.
- `processing/` — czyszczenie, deduplikacja, PII/toks, segmentacja, tagowanie, klasyfikacja ryzyk.
- `datasets/` — budowa warstw clean/curated, split eval/safety, raporty.
- `ml/` — przygotowanie SFT, ewaluacja, guardrails inference.
- `ops/` — CLI, schedulery, DVC/IaC glue.
- `tests/` — unit/integration/snapshot.
- `config/` — `config.yaml`, `.env.example`, progi toks/PII, ścieżki S3.

## Wymagane skrypty (Python)
- `ingest/rss_fetcher.py` — pobór RSS/API z whitelisty, zapis raw+meta.
- `ingest/crawler.py` — crawler z robots.txt, rate-limit, retry.
- `ingest/license_checker.py` — walidacja licencji, aktualizacja whitelist/blacklist.
- `scripts/verify_feeds.py` — robots/head check + raport + opcjonalny update robots_ok.
- `processing/clean_normalize.py` — normalizacja tekstu/HTML.
- `processing/dedupe.py` — hash + minhash/SimHash, odrzucanie duplikatów.
- `processing/pii_scrubber.py` — detekcja/usuwanie PII (NER+regex).
- `processing/toxicity_filter.py` — scoring toksyczności (Detoxify/Perspective wrapper).
- `processing/lang_detect.py` — heurystyczne oznaczanie języka.
- `processing/tagger.py` — heurystyczne tagi tematów/tonu.
- `processing/segmenter.py` — podział na akapity/sekcje z metadanymi.
- `processing/tagger.py` — klasyfikacja tematów i tonu (model + heurystyki).
- `processing/risk_classifier.py` — flagi defamacja/nawoływanie/dezinformacja.
- `datasets/build_corpora.py` — warstwy clean/curated, Parquet/JSONL, manifesty.
- `datasets/split_eval_sets.py` — zbalansowane eval/safety sety.
- `datasets/stats_report.py` — raport coverage, toksyczność, odrzucenia.
- `ml/prepare_sft_data.py` — formatowanie instrukcji (prompt/output/kontekst).
- `ml/eval_suite.py` — eval stylu/bezpieczeństwa/jailbreak, raport do wandb/MLflow.
- `ml/guardrails_inference.py` — filtry safety/PII/tone do runtime.
- `ops/dvc_stage_builder.py` — generacja `dvc.yaml`/`params.yaml`.
- `ops/cli.py` — wejście główne (`satyrai ingest|clean|stats|eval`).
- `ops/scheduler_jobs.py` — joby cron (Prefect/Airflow) łączące powyższe kroki.

## Konfiguracja i uruchamianie
- WSL/Unix środowisko, Python 3.10+.
- `pip install -r requirements.txt` (zależności: httpx/requests, bs4/readability, pandas/pyarrow, detoxify, spacy/transformers, sentence-transformers, wandb/mlflow, dvc, pydantic/yaml).
- `.env` dla sekretów (API toksyczności, endpointy), `config.yaml` dla progów i ścieżek (`s3://satyrai/raw|clean|curated|eval`).
- Logi strukturalne (JSON) do stdout + zapisy do `logs/`.

## Przepływ referencyjny
1) `ingest/rss_fetcher.py` / `crawler.py` → `raw/`.
2) `license_checker.py` (fail fast na braku licencji); `scripts/verify_feeds.py` do robots/status.
3) `clean_normalize.py` → `dedupe.py`.
4) `pii_scrubber.py` → `toxicity_filter.py` (odrzucone do quarantine).
5) `lang_detect.py` → `tagger.py` → `segmenter.py` → `risk_classifier.py`.
6) `build_corpora.py` → `split_eval_sets.py` → `stats_report.py` → `export_training_jsonl.py`.
7) `prepare_sft_data.py` → trening (osobny repo/notebook) → `eval_suite.py`.
8) `guardrails_inference.py` używane w serwisie generacji.

## Testy i jakość
- Unit testy dla parsowania, deduplikacji, taggerów, guardrails.
- Snapshot testy na pipeline (małe paczki) — porównanie manifestów/stats.
- Eval/regresja promptów: `ml/eval_suite.py` z baseline wynikami; blokuj release gdy metryki spadną.

## Operacje
- Orkiestracja: Prefect/Airflow DAG z etapami ingest→clean→tag→stats→eval.
- Wersjonowanie: DVC (dane), MLflow/wandb (modele).
- Alerty: job failure, wzrost toksyczności, drifty metryk.

