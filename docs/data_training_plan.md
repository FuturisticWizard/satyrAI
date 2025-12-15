# Plan danych i treningu modelu SatyrAI

## 1. Cele treningu
- Uzyskać model generujący spójne, satyryczne treści polityczne w tonie libertariańskim.
- Minimalizować toksyczność, halucynacje i ryzyko prawne; utrzymać styl humorystyczny.
- Zapewnić kontrolę wersji danych/modeli i możliwość szybkiego rollbacku.

## 2. Źródła danych
- Publiczne artykuły i wpisy publicystyczne o profilu libertariańskim (RSS, archiwa).
- Blogi i felietony satyryczne (po weryfikacji licencji).
- Metadane: autor, data, licencja, tematy, ton, region, język.
- Czarna lista: domeny o niejasnej licencji; usuwamy dane niezgodne z polityką.

## 3. Proces pozyskania i czyszczenia
- Crawling/ingestion (RSS/API/manualne batch’e) → zapis w Data Lake (np. s3://satyrai/raw).
- Filtry: deduplikacja (hash), usunięcie PII, filtrowanie wulgarności, normalizacja znaków.
- Segmentacja: akapity/sekcje, tagowanie tematów i tonu (semi-automatyczne + annotatorzy).
- Licencje: każdy dokument z polem license + źródło.

## 4. Adnotacje i etykiety
- Ton: satyra, ironia, komentarz, mem.
- Tematy: podatki, wolność słowa, regulacje, polityka zagraniczna, gospodarka.
- Ryzyko: defamacja, wrażliwe grupy, nawoływanie, miz/informacja.
- Styl referencyjny: embedding wzorcowych tekstów (biblioteka referencyjna).

## 5. Zbiory danych
- **Pretrain/continual corpus**: oczyszczone teksty (LM finetune/continual).
- **Instrukcje**: (prompt, output) z kontekstem stylu; warianty długości (krótkie/średnie/długie).
- **Eval set**: równowaga tematów/tonów; zawiera przykłady wrażliwe do testów bezpieczeństwa.
- **Safety set**: zestaw czarnych scenariuszy (nawoływanie, defamacja, dezinformacja) do oceny guardrails.

## 6. Augmentacja i kontekst
- Retrieval z zaufanych źródeł news (cache dzienny) do wzmacniania factuality.
- Kontekst stylu: wstrzyknięcie przykładów referencyjnych i wytycznych tonu.
- Red teaming: generowanie kontra-przykładów, perturbacje promptów.

## 7. Trening
- Strategia: instrukcyjne finetune (SFT) na curated instrukcjach + LoRA/QLoRA dla efektywności kosztowej.
- Hparamy (wstępnie): lr 2e-4, batch 64 eff, max seq 2048, warmup 5%, cosine decay.
- Regularizacja: label smoothing dla instrukcji, dropout, gradient clipping.
- Checkpointing: co 1k step, early stop na eval loss i metrykach stylu/bezpieczeństwa.
- Infrastrukturę: GPU A100/L4; orchestracja: Prefect/Airflow + wandb/MLflow.

## 8. Ewaluacja
- Styl: similarity do korpusu referencyjnego (embeddings), human rating (3–5 punktów).
- Bezpieczeństwo: toxicity score (Perspective/Detoxify), klasyfikator wrażliwości, jailbreak tests.
- Factuality: LLM judge + retrieval grounding; penalizacja halucynacji.
- Spójność tonu libertariańskiego: klasyfikator tematyczny + stylowy.
- Raportowanie: dashboard (Prometheus/Grafana) + raport PDF/HTML per release.

## 9. MLOps i wersjonowanie
- Dane: DVC/Git LFS; modele: registry (MLflow/HF hub private).
- Artefakty: zestawy danych, config treningu, checkpointy, eval raport.
- CI/CD: testy statyczne promptów, eval safety/stylu przed deploy; canary/champion-challenger.
- Rollback: poprzedni model + kompatybilne guardrails + cached prompts.

## 10. Inference i guardrails
- Warstwa RAG opcjonalna: krótkie fakty polityczne z cache (TTL 24h).
- Guardrails: klasyfikator bezpieczeństwa, filtry wrażliwych tematów, blokada P0, rewizja manualna P1.
- Logging: prompt, kontekst, wersja modelu, decyzje filtrów, output id.
- Cost controls: batching, cache kontekstu, limity per requester.

## 11. Feedback loop
- Zbieranie ocen redaktorów (jakość, humor, ryzyko).
- Automatyczne etykietowanie błędów (halucynacja, ton off-brand, toksyczność).
- Cotygodniowa inkrementalna aktualizacja korpusu + okresowy finetune po przejściu eval.

