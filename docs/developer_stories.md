# Developer Stories — SatyrAI pipelines

## Epic A: Ingestion i licencje
- Story A1: Jako developer chcę pobrać feedy RSS/API z whitelisty, aby mieć świeże artykuły w `raw/`.
  - Kryteria: obsługa RSS/Atom/JSON, retry, robots.txt, metadane (URL, data, autor, license).
- Story A2: Jako developer chcę crawlera fallback dla źródeł bez RSS.
  - Kryteria: rate-limit, user-agent, parsowanie HTML→tekst, log blokad.
- Story A3: Jako developer chcę walidować licencje i aktualizować whitelist/blacklist.
  - Kryteria: parser licencji, fail fast przy braku, raport odrzuceń.

## Epic B: Czyszczenie i filtrowanie
- Story B1: Jako developer chcę normalizować teksty i usuwać artefakty HTML.
  - Kryteria: usuwanie tagów, encji, standaryzacja znaków, zapis diff (opcjonalnie).
- Story B2: Jako developer chcę deduplikować treści, aby uniknąć powtórek w korpusie.
  - Kryteria: hash pełny + minhash/SimHash, progi podobieństwa, raport duplikatów.
- Story B3: Jako developer chcę usuwać PII z tekstów.
  - Kryteria: NER + regex, log usuniętych bytów, wskaźnik false positive.
- Story B4: Jako developer chcę filtrować toksyczne treści.
  - Kryteria: scoring (Detoxify/Perspective), próg konfigurowalny, kubeł `quarantine/`.

## Epic C: Segmentacja, tagowanie, ryzyka
- Story C1: Jako developer chcę segmentować dokumenty na akapity/sekcje z metadanymi.
  - Kryteria: stabilne ID segmentu, link do oryginalnego URL, offsety.
- Story C2: Jako developer chcę automatycznie tagować tematy i ton (satyra/ironia/komentarz).
  - Kryteria: model klasyfikacji + fallback regułowy, confidence, możliwość ręcznego override.
- Story C3: Jako developer chcę klasyfikować ryzyka (defamacja, nawoływanie, dezinformacja).
  - Kryteria: flagi P0/P1, eksport do safety setu, log decyzji.

## Epic D: Budowa zbiorów i raporty
- Story D1: Jako developer chcę zbudować warstwy `clean/curated` i manifesty.
  - Kryteria: zapis Parquet/JSONL, checksumy, schema, counts per tag.
- Story D2: Jako developer chcę przygotować eval i safety sety z balansem tematów/tonu.
  - Kryteria: sampling kontrolowany, statystyki rozkładu, snapshot version.
- Story D3: Jako developer chcę raport coverage/toks/odrzuceń.
  - Kryteria: raport CSV/HTML, metryki toksyczności, udział odrzuceń, top źródeł.

## Epic E: Trening i guardrails
- Story E1: Jako developer chcę przygotować dane SFT (prompt/output/kontekst).
  - Kryteria: JSONL w standardowym formacie, sanity checks długości, rozkład tematów.
- Story E2: Jako developer chcę automatyczny eval stylu/bezpieczeństwa/jailbreak.
  - Kryteria: raport do wandb/MLflow, progi blokujące release, artefakt HTML.
- Story E3: Jako developer chcę moduł guardrails do inference.
  - Kryteria: funkcje API (tox, PII, ryzyko), konfiguracja progów, logowanie decyzji.

## Epic F: Ops i narzędzia
- Story F1: Jako developer chcę CLI spinające kroki pipeline.
  - Kryteria: `satyrai ingest|clean|stats|eval`, spójne logi, kody wyjścia.
- Story F2: Jako developer chcę joby do schedulerów (Prefect/Airflow).
  - Kryteria: DAG ingest→clean→tag→stats→eval, alerty na failure, parametryzacja.
- Story F3: Jako developer chcę DVC stage builder dla danych.
  - Kryteria: generacja `dvc.yaml`/`params.yaml`, cache ścieżek, lock wersji.

