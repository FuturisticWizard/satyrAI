"""
Pobiera content z nowych źródeł - Faza 1.
Wykorzystuje istniejący rss_fetcher.py ale tylko dla nowych źródeł.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from ingest.rss_fetcher import fetch_feed, rate_limit_sleep, slugify
import json

# Nowe źródła do scrapowania (działające)
NEW_SOURCES = [
    {
        "name": "Independent Institute",
        "feed": "https://www.independent.org/feed/",
        "type": "opinion",
        "country": "US", 
        "license": "permissive",
        "rate_limit_rps": 0.2
    },
    {
        "name": "AIER",
        "feed": "https://www.aier.org/feed/", 
        "type": "opinion",
        "country": "US",
        "license": "permissive",
        "rate_limit_rps": 0.2
    },
    {
        "name": "Niezalezna",
        "feed": "https://niezalezna.pl/feed/",
        "type": "opinion", 
        "country": "PL",
        "license": "permissive",
        "rate_limit_rps": 0.1
    }
]

def fetch_new_sources():
    """Pobiera artykuły z nowych źródeł."""
    print("=== POBIERANIE NOWYCH ŹRÓDEŁ - FAZA 1 ===\n")
    
    total_fetched = 0
    
    for source in NEW_SOURCES:
        print(f"Fetching: {source['name']}")
        print(f"URL: {source['feed']}")
        
        try:
            # Fetch articles from this source 
            articles = list(fetch_feed(
                url=source['feed'],
                user_agent="SatyrAI-bot/0.1"
            ))
            
            if articles:
                print(f"  ✅ Pobrano: {len(articles)} artykułów")
                total_fetched += len(articles)
                
                # Dodaj metadane do każdego artykułu
                enriched_articles = []
                for article in articles:
                    enriched = {
                        "source": source['name'],
                        "feed": source['feed'],
                        "type": source['type'],
                        "country": source['country'],
                        "license": source['license'],
                        "data": article
                    }
                    enriched_articles.append(enriched)
                
                # Save to separate file for new sources
                slug = slugify(source['name'])
                output_file = ROOT / "data" / "raw" / f"new-{slug}.jsonl"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with output_file.open('w', encoding='utf-8') as f:
                    for enriched in enriched_articles:
                        f.write(json.dumps(enriched, ensure_ascii=False) + '\n')
                
                print(f"  💾 Zapisano do: {output_file}")
            else:
                print(f"  ❌ Brak artykułów")
                
        except Exception as e:
            print(f"  ❌ Błąd: {e}")
            
        # Rate limiting
        rate_limit_sleep(source['rate_limit_rps'])
        print()
    
    print(f"=== PODSUMOWANIE ===")
    print(f"Łącznie pobrano: {total_fetched} nowych artykułów")
    print(f"Lokalizacja: {ROOT}/data/raw/new-*.jsonl")
    
    return total_fetched

if __name__ == "__main__":
    fetch_new_sources()