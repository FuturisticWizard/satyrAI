# Architektura systemu SatyrAI

## 1. Widok całości
- **ETL/ELT**: zewnętrzne feedy (RSS/API) → kolejka (Kafka/SQS) → przetwarzanie (dbt/Spark/Batch) → Data Lake.
- **Repo danych**: warstwa raw/clean/curated, wersjonowanie (DVC), metadane licencji.
- **Trening/Finetune**: orkiestracja (Prefect/Airflow), joby GPU (K8s), logging (wandb/MLflow), model registry.
- **Inference API**: serwis generacji (FastAPI/Node), opcjonalny RAG (vector store + news cache), guardrails (safety classifier, PII/tone filters).
- **Redakcja**: panel web (Next.js) → workflow draft → review → publikacja (CMS adapter / Markdown).
- **Observability**: Prometheus/Grafana + strukturalne logi; alerty P0/P1; audyt promptów/outów.

## 2. Komponenty i odpowiedzialności
- Ingestion: harmonogram pobrań, deduplikacja, licencje, tagowanie tematów/tonu.
- Data processing: czyszczenie, filtry wulgarności, adnotacje pół-automatyczne.
- Feature/Corpus store: przechowywanie segmentów tekstu, embeddingów referencyjnych.
- Training pipeline: SFT/LoRA, automatyczne eval (styl/bezpieczeństwo/fakty), rejestracja modeli.
- Serving: API v1 `/generate`, `/moderate`, `/suggest-topics`, wersja modelu w nagłówkach.
- Moderacja/Guardrails: klasyfikator bezpieczeństwa, blokady P0, rewizja manualna P1, polityka stylu.
- Redakcyjny workflow: kolejka tematów, edytor, historia wersji, publikacja do CMS lub statyczny eksport.
- Storage publikacji: bucket + CDN lub headless CMS (np. Ghost/Strapi) albo generacja statyczna.
- Telemetria: trace id dla całej ścieżki (dane→model→post), metryki kosztów (tokeny, GPU), A/B eksperymenty tonów.

## 3. Przepływy
- **Treść z briefu**: brief → `/generate` (kontekst stylu + referencje) → guardrails → draft → redakcja → publikacja.
- **Treść z harmonogramu**: cron → wybór tematu (feed + heurystyki) → generacja → moderacja → publikacja.
- **Feedback loop**: oceny redaktorów → logi jakości → kolejka poprawkowa → dataset increment → następny finetune.
- **Model release**: nowy checkpoint → eval suite → champion/challenger → rollout canary → pełny rollout/rollback.

## 4. Integracje i interfejsy
- Ingress: REST/GraphQL do panelu, webhooki feedów, cron jobs ingestion.
- Egress: CMS adapter (Ghost/WordPress API) lub eksport Markdown/HTML + RSS/Newsletter.
- AuthN/AuthZ: OIDC (np. Auth0/Keycloak); role: admin, redaktor, viewer; rate limits na API.
- Secret management: vault/KMS; brak sekretów w kodzie.

## 5. Bezpieczeństwo i zgodność
- Filtry toksyczności, słowa kluczowe wysokiego ryzyka, blokady tematów wrażliwych.
- Logowanie decyzji moderacji (kto/ kiedy, wersja modelu, prompt).
- Privacy: brak PII w danych treningowych; skan PII; zgodność licencji.
- Audyt: immutable log (append-only), możliwość eksportu raportu incydentów.

## 6. Monitoring i SLO
- SLO: 99.5% dostępności API generacji; P99 latency < 8 s (z cache kontekstu).
- Alerty: wzrost toksyczności > prog, odsetek odrzuconych draftów, błędy 5xx, koszty GPU.
- Dashboardy: ruch, latency, koszty per model, sukces publikacji, jakość stylu (embedding drift).

## 7. Operacje i narzędzia
- Infra: Kubernetes lub ECS + autoscaling; storage: S3/GCS; CDN dla treści.
- CI/CD: testy lint/prompt/regresja stylu, deploy modeli i aplikacji; IaC (Terraform).
- Zarządzanie kosztami: limity tokenów, cache, batchowanie, harmonogramy zadań GPU.

