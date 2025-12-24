"""
Pobiera content z działających źródeł Fazy 2.
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from ingest.rss_fetcher import fetch_feed, rate_limit_sleep, slugify
import json

# FAZA 2 - działające źródła
PHASE2_SOURCES = [
    {
        "name": "wPolityce (Feedburner)",
        "feed": "http://feeds.feedburner.com/wPolitycepl",
        "type": "opinion",
        "country": "PL",
        "license": "permissive", 
        "rate_limit_rps": 0.1
    },
    {
        "name": "Legal Insurrection",
        "feed": "https://legalinsurrection.com/feed/",
        "type": "opinion",
        "country": "US",
        "license": "permissive",
        "rate_limit_rps": 0.2
    },
    {
        "name": "PJ Media",
        "feed": "https://pjmedia.com/feed",
        "type": "opinion", 
        "country": "US",
        "license": "permissive",
        "rate_limit_rps": 0.2
    },
    {
        "name": "American Conservative",
        "feed": "https://www.theamericanconservative.com/feed/",
        "type": "opinion",
        "country": "US", 
        "license": "permissive",
        "rate_limit_rps": 0.2
    }
]

def fetch_phase2_sources():
    """Pobiera artykuły z źródeł Fazy 2."""
    print("=== POBIERANIE ŹRÓDEŁ FAZY 2 ===\n")
    
    total_fetched = 0
    
    for source in PHASE2_SOURCES:
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
                
                # Save to separate file for Phase 2 sources
                slug = slugify(source['name'])
                output_file = ROOT / "data" / "raw" / f"phase2-{slug}.jsonl"
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
    
    print(f"=== PODSUMOWANIE FAZY 2 ===")
    print(f"Łącznie pobrano: {total_fetched} nowych artykułów")
    print(f"Lokalizacja: {ROOT}/data/raw/phase2-*.jsonl")
    
    return total_fetched

if __name__ == "__main__":
    fetch_phase2_sources()