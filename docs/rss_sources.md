# RSS — propozycje źródeł (whitelist draft)

> Uwaga: zweryfikuj licencje (CC/explicit), politykę robots.txt i zgodność z profilem libertariańskim/satyrycznym przed włączeniem do produkcji. Odrzucaj źródła z niejasnymi prawami lub paywallem twardym.

## 1. Portale libertariańskie / wolnorynkowe
- Reason Magazine — https://reason.com/feed/
- Cato Institute — https://www.cato.org/rss
- Foundation for Economic Education (FEE) — https://fee.org/articles/rss/
- Mises Institute — https://mises.org/rss.xml
- Libertarian Institute — https://libertarianinstitute.org/feed/
- American Institute for Economic Research (AIER) — https://www.aier.org/feed/
- Adam Smith Institute (UK) — https://www.adamsmith.org/feed
- Competitive Enterprise Institute — https://cei.org/feed/
- Quillette (klasyczny liberalizm) — https://quillette.com/feed/

## 2. Publicystyka / opinie (z ostrożnością, selektywnie)
- City Journal — https://www.city-journal.org/feed
- The Spectator (komentarze) — https://www.spectator.co.uk/feed
- The Dispatch — https://thedispatch.com/feed/
- UnHerd — https://unherd.com/feed/
- CapX — https://capx.co/feed/
- Spiked — https://www.spiked-online.com/feed/

## 3. Technologie / wolność słowa / prywatność (dodatkowy kontekst)
- EFF Deeplinks — https://www.eff.org/rss/updates.xml
- Techdirt — https://www.techdirt.com/feed/
- OSNews — https://www.osnews.com/feed/

## 4. Satyra / humor polityczny (sprawdź licencje!)
- The Babylon Bee — https://babylonbee.com/feed
- The Onion — https://www.theonion.com/rss
- Duffel Blog (satyr. wojsko) — https://www.duffelblog.com/feed
- Waterford Whispers News — https://waterfordwhispersnews.com/feed/
- Private Eye (sprawdzić licencję) — https://www.private-eye.co.uk/rss
- The Poke — https://www.thepoke.co.uk/feed/

## 5. Polskie (do weryfikacji licencji i tonu)
- Warsaw Enterprise Institute (WEI) — https://wei.org.pl/feed/
- FOR (Forum Obywatelskiego Rozwoju) — https://for.org.pl/pl/rss
- Instytut Misesa PL — https://mises.pl/feed/
- Blogi wolnorynkowe (kuracja ręczna; sprawdzić licencje/roboty)
- Libertarianizm.pl — https://libertarianizm.pl/feed/
- Satyra polityczna / komentarz:
  - Aszdziennik — https://aszdziennik.pl/rss (sprawdzić prawa/licencję)
  - Donald.pl — https://www.donald.pl/rss (sprawdzić prawa/licencję)
  - Antyweb publicystyka (tech + wolność słowa) — https://antyweb.pl/rss
  - Subiektywnie o finansach (publicystyka gospodarcza) — https://subiektywnieofinansach.pl/feed/
- Lokalne/regionalne blogi libertariańskie: wymagają ręcznej kuracji i potwierdzenia licencji.

## 6. Listy kontrolne przy dodawaniu źródła
- Sprawdź `robots.txt` i nagłówki licencyjne.
- Czy feed jest pełny czy tylko nagłówki? (jeśli tylko nagłówki, użyj crawlera z respektowaniem licencji).
- Oceń profil ideowy (libertariański/wolnorynkowy) i poziom satyry.
- Dodaj do whitelisty z polami: `name`, `url`, `license`, `type` (news/opinion/satire), `country`, `notes`.
- Ustal limit pobrań (rate limit) i kategorie tagów (ekonomia/podatki/wolność słowa/…).

## 7. Blacklist / odradzane
- Źródła z twardym paywallem lub niejasnymi prawami autorskimi.
- Agregatory kopiujące treści bez licencji.

## 8. Przykładowy wpis whitelist (YAML)
```yaml
- name: "Reason Magazine"
  feed: "https://reason.com/feed/"
  type: "opinion"
  country: "US"
  license: "check"   # CC BY-NC? brak? uzupełnij po weryfikacji
  robots_ok: true
  tags: ["libertarian", "politics", "economics", "satire-light"]
  rate_limit_rps: 0.2
  notes: "Sprawdzić sekcję Terms of Use przed produkcją."
```

