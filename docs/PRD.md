# PRD — Portal satyryczno‑polityczny „SatyrAI”

## 1. Cel i wizja
- **Cel**: Stworzenie portalu prezentującego satyryczne treści polityczne o profilu libertariańskim, generowane i wspierane przez dedykowany model LLM wytrenowany na wyselekcjonowanych artykułach i wpisach.
- **Wizja**: Automatyczny, bezpieczny i spójny pipeline — od pozyskania danych, przez trening/utrzymanie modelu, po generowanie i publikację treści blogowych z moderacją i audytem.

## 2. Użytkownicy i potrzeby
- Czytelnicy: szybki dostęp do świeżych, błyskotliwych wpisów satyrycznych zgodnych z libertariańskim tonem.
- Redakcja/kuratorzy: możliwość zatwierdzania tematów, przeglądu draftów, korekty i publikacji.
- Administratorzy/ML Ops: monitorowanie jakości modelu, bezpieczeństwa treści i stanu pipeline’u.

## 3. Zakres funkcjonalny
- Generowanie treści blogowych (artykuły, krótkie wpisy, memokomentarze) wg promptów lub harmonogramu.
- Panel redakcyjny: kolejka tematów, podgląd wersji roboczych, edycja, akceptacja/odrzucenie, publikacja.
- Moderacja: filtry bezpieczeństwa (polityka bezpieczeństwa i stylu), klasyfikatory ryzyka, blacklist/whitelist źródeł i bytów.
- Harmonogram publikacji i autoposting (RSS/Newsletter/API do CMS lub statyczne generowanie).
- Telemetria: logi wygenerowanych treści, ścieżka danych, ocena jakości (human + automatyczne klasyfikatory), feedback loop.
- Obsługa A/B testów tonów/formatów postów.

### Poza zakresem (obecna faza)
- Komentarze użytkowników i forum.
- Funkcje społecznościowe wykraczające poza share/link.
- Pełna personalizacja per użytkownik (możliwa w roadmapie).

## 4. Wymagania biznesowe / KPI
- ≥ 80% treści zaakceptowanych po pierwszej iteracji moderacji.
- Czas od pomysłu do publikacji: < 2h (w tym QA).
- Drift jakości: < 5% spadku metryk semantycznych miesiąc do miesiąca.
- Zero krytycznych naruszeń polityki bezpieczeństwa (P0).

## 5. Wymagania funkcjonalne (skrót)
- Definiowanie tematów/briefów (ręcznie lub z feedów news/API).
- Generowanie wersji roboczej przez LLM z kontekstem stylu libertariańskiego i bazą faktów.
- Moduł fact-check stub: flagowanie fragmentów wymagających weryfikacji.
- Edytor redakcyjny z historią zmian i podpisem autora/LLM.
- Workflow akceptacji: draft → redakcja → akceptacja → publikacja.
- Publikacja do CMS/Markdown/HTML oraz RSS.
- Telemetria: zapisywanie promptów, wersji modelu, danych wejściowych i oceny.

## 6. Wymagania niefunkcjonalne
- Jakość: testy automatyczne promptów (regresja stylu i bezpieczeństwo).
- Wydajność: generacja pojedynczego wpisu ≤ 10 s (przy cache kontekstu).
- Bezpieczeństwo: filtry toksyczności, polityka tematów wrażliwych, audyt logów.
- Prywatność: przechowywanie tylko publicznych/zezwolonych danych, RODO/GDPR check.
- Observability: tracing żądań, metryki wykorzystania modelu, alerty P0/P1.

## 7. Dane i trening (wysoki poziom)
- Źródła: artykuły i wpisy publicystyczne (libertariańskie), metadane (data, autor, licencja), tagi tematyczne.
- Czyszczenie: deduplikacja, normalizacja, usuwanie PII, filtry wulgarności.
- Adnotacje: ton (satyra, ironia), temat (ekonomia, wolność słowa, podatki), ryzyka (defamacja, wrażliwość).
- Zestawy: pretrain corpus, instrukcje (prompt → output), eval set (styl + bezpieczeństwo).
- Metryki: semantyczne (BLEU/ROUGE/Meteor opcjonalnie), styl (embedding similarity do wzorców), bezpieczeństwo (toxicity score), factuality (LLM judge + retrieval).

## 8. Architektura produktu (skrót)
- Ingestion (ETL/ELT) → Data Lake → Feature Store/Corpus Store → Training/Finetune → Model Registry → Inference API → Moderacja/Guardrails → Redakcja → Publikacja → Observability.
- CMS adapter: eksport do Markdown/HTML + RSS/Newsletter.
- MLOps: wersjonowanie danych (DVC/Git LFS), modele (registry), deployment (container/serverless), testy regresji promptów.

## 9. User stories (przykłady)
- Jako redaktor chcę wprowadzić temat „nowa ustawa podatkowa” i otrzymać draft satyryczny z 2 wariantami tonu.
- Jako redaktor chcę oznaczyć fragment do fact-checku i wrócić z poprawioną wersją.
- Jako admin chcę widzieć alerty, gdy model generuje treści ryzykowne.

## 10. Roadmap (wysoki poziom)
- Faza 0: Setup repo, skeleton pipeline, zbiór próbek, wstępne prompty, baseline eval.
- Faza 1: ETL + korpus, pierwsze finetune, redakcyjny MVP, moderacja statyczna.
- Faza 2: Guardrails + automatyczne testy stylu/bezpieczeństwa, A/B tonów, harmonogram publikacji.
- Faza 3: Rozszerzenia (newsletter, personalizacja lekka), ciągły retraining na feedbacku.

## 11. Ryzyka i mitigacje
- Ryzyko prawne/licencyjne źródeł → whitelist, weryfikacja licencji, log źródeł.
- Ryzyko halucynacji/fake news → retrieval z wiarygodnych źródeł + fact-check queue.
- Ryzyko politycznych nadużyć → polityka treści, filtry wrażliwych tematów, audyt.
- Drift stylu → eval regresyjny per release, rollbacks, champion/challenger.
- Ucieczka kosztów inferencji → batching, cache, limity, monitorowanie kosztów tokenów.


