#!/usr/bin/env python3
"""
Analiza techniczna stron polskich blogów prawicowych/libertariańskich
Testuje różne techniki scrapingu i określa najlepszą strategię dla każdego serwisu.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional
import logging

# Konfiguracja
SITES_TO_ANALYZE = {
    "salon24": {
        "base_url": "http://www.salon24.pl",
        "test_pages": [
            "/blogi/polityka",
            "/u/wybor-redakcji",
        ],
        "robots_delay": 1  # z robots.txt
    },
    "mises": {
        "base_url": "https://mises.pl", 
        "test_pages": [
            "/blog",
            "/artykuly",
        ],
        "robots_delay": 0  # brak ograniczeń
    },
    "libertarianizm": {
        "base_url": "https://libertarianizm.pl",
        "test_pages": [
            "/",
            "/forum",
        ],
        "robots_delay": 0  # prawdopodobnie brak ograniczeń
    },
    "wpolityce": {
        "base_url": "https://wpolityce.pl",
        "test_pages": [
            "/opinie",
            "/polityka",
        ],
        "robots_delay": 0  # do weryfikacji
    }
}

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def get_page_with_delay(url: str, delay: float = 0) -> Optional[requests.Response]:
    """Pobiera stronę z respektowaniem robots.txt delay"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SatyrAI-Research/1.0; Educational research)'
    }
    
    try:
        if delay > 0:
            time.sleep(delay)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except Exception as e:
        logging.error(f"Błąd pobierania {url}: {e}")
        return None

def analyze_page_structure(response: requests.Response, site_name: str) -> Dict:
    """Analizuje strukturę HTML strony"""
    soup = BeautifulSoup(response.content, 'html.parser')
    
    analysis = {
        "site": site_name,
        "url": response.url,
        "status_code": response.status_code,
        "content_length": len(response.content),
        "has_javascript": bool(soup.find_all('script')),
        "meta_tags": len(soup.find_all('meta')),
        "links": len(soup.find_all('a')),
        "articles": len(soup.find_all(['article', 'div[class*="post"]', 'div[class*="blog"]'])),
        "pagination": bool(soup.find(['nav', 'div'], class_=['pagination', 'pager', 'page-nav'])),
        "infinite_scroll_indicators": bool(soup.find(['div', 'button'], class_=['load-more', 'infinite', 'scroll'])),
        "rss_feed": bool(soup.find('link', {'type': 'application/rss+xml'})),
        "encoding": response.encoding,
    }
    
    # Szukaj struktury artykułów/postów
    article_selectors = [
        'article',
        '.post',
        '.blog-post', 
        '.entry',
        '.article',
        '[class*="post"]',
        '[class*="blog"]',
        '[class*="entry"]'
    ]
    
    found_selectors = []
    for selector in article_selectors:
        elements = soup.select(selector)
        if elements:
            found_selectors.append({
                "selector": selector,
                "count": len(elements),
                "sample_class": elements[0].get('class', []) if elements else []
            })
    
    analysis["article_selectors"] = found_selectors
    
    # Sprawdź czy jest API/JSON endpoint
    json_scripts = soup.find_all('script', string=lambda text: text and ('api' in text.lower() or 'json' in text.lower()))
    analysis["has_api_endpoints"] = len(json_scripts) > 0
    
    return analysis

def detect_scraping_challenges(analysis: Dict) -> List[str]:
    """Wykrywa potencjalne wyzwania scrapingu"""
    challenges = []
    
    if analysis["has_javascript"]:
        challenges.append("JavaScript-heavy (może wymagać Selenium)")
    
    if analysis["infinite_scroll_indicators"]:
        challenges.append("Infinite scroll (wymaga emulacji przewijania)")
    
    if analysis["content_length"] < 10000:
        challenges.append("Mała zawartość (może być dynamicznie ładowana)")
    
    if not analysis["article_selectors"]:
        challenges.append("Brak jasnej struktury artykułów")
    
    if analysis["has_api_endpoints"]:
        challenges.append("Możliwy API endpoint (sprawdź network tab)")
    
    return challenges

def recommend_scraping_strategy(analysis: Dict, challenges: List[str]) -> Dict:
    """Rekomenduje strategię scrapingu"""
    strategy = {
        "primary_method": "requests + BeautifulSoup",
        "backup_method": None,
        "rate_limit": 1.0,  # domyślnie 1 sekunda
        "use_selenium": False,
        "best_selectors": [],
        "notes": []
    }
    
    # Ustaw rate limit z robots.txt
    if analysis.get("robots_delay", 0) > 0:
        strategy["rate_limit"] = max(strategy["rate_limit"], analysis["robots_delay"])
    
    # Sprawdź wyzwania
    if "JavaScript-heavy" in challenges:
        strategy["primary_method"] = "Selenium + BeautifulSoup" 
        strategy["backup_method"] = "requests + BeautifulSoup"
        strategy["use_selenium"] = True
        strategy["notes"].append("Użyj Selenium dla dynamicznej zawartości")
    
    if "Infinite scroll" in challenges:
        strategy["use_selenium"] = True
        strategy["notes"].append("Zaimplementuj przewijanie w Selenium")
    
    if analysis.get("rss_feed"):
        strategy["backup_method"] = "RSS feed parsing"
        strategy["notes"].append("RSS feed dostępny jako alternatywa")
    
    # Wybierz najlepsze selektory
    if analysis.get("article_selectors"):
        # Sortuj według liczby znalezionych elementów
        sorted_selectors = sorted(
            analysis["article_selectors"], 
            key=lambda x: x["count"], 
            reverse=True
        )
        strategy["best_selectors"] = [s["selector"] for s in sorted_selectors[:3]]
    
    return strategy

def main():
    setup_logging()
    results = []
    
    print("🔍 Analiza techniczna polskich blogów prawicowych/libertariańskich\n")
    
    for site_name, config in SITES_TO_ANALYZE.items():
        print(f"📊 Analizuję: {site_name} ({config['base_url']})")
        
        site_results = {
            "site": site_name,
            "config": config,
            "pages": [],
            "overall_strategy": None
        }
        
        for test_page in config["test_pages"]:
            url = urljoin(config["base_url"], test_page)
            print(f"   📄 Testuje: {url}")
            
            # Pobierz stronę z delay
            response = get_page_with_delay(url, config["robots_delay"])
            
            if not response:
                continue
                
            # Analizuj strukturę
            analysis = analyze_page_structure(response, site_name)
            
            # Wykryj wyzwania
            challenges = detect_scraping_challenges(analysis)
            
            # Rekomenduj strategię
            strategy = recommend_scraping_strategy(analysis, challenges)
            
            page_result = {
                "url": url,
                "analysis": analysis,
                "challenges": challenges,
                "strategy": strategy
            }
            
            site_results["pages"].append(page_result)
            
            # Wyświetl wyniki
            print(f"      ✅ Status: {analysis['status_code']}")
            print(f"      📏 Rozmiar: {analysis['content_length']:,} bajtów")
            print(f"      🔗 Linków: {analysis['links']}")
            print(f"      📰 Artykułów: {analysis['articles']}")
            print(f"      ⚠️  Wyzwania: {', '.join(challenges) if challenges else 'Brak'}")
            print(f"      💡 Metoda: {strategy['primary_method']}")
            print(f"      ⏱️  Rate limit: {strategy['rate_limit']}s")
            print()
        
        # Określ strategię dla całego serwisu
        if site_results["pages"]:
            # Weź strategię z pierwszej działającej strony
            site_results["overall_strategy"] = site_results["pages"][0]["strategy"]
        
        results.append(site_results)
    
    # Zapisz wyniki
    output_file = "scraping_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Wyniki zapisane do: {output_file}")
    
    # Podsumowanie
    print("\n" + "="*60)
    print("📋 PODSUMOWANIE REKOMENDACJI")
    print("="*60)
    
    for result in results:
        site_name = result["site"]
        strategy = result.get("overall_strategy", {})
        
        print(f"\n🎯 {site_name.upper()}:")
        print(f"   Metoda: {strategy.get('primary_method', 'N/A')}")
        print(f"   Rate limit: {strategy.get('rate_limit', 'N/A')}s")
        print(f"   Selenium: {'Tak' if strategy.get('use_selenium') else 'Nie'}")
        
        if strategy.get("best_selectors"):
            print(f"   Selektory: {', '.join(strategy['best_selectors'][:2])}")
        
        if strategy.get("notes"):
            print(f"   Uwagi: {'; '.join(strategy['notes'])}")

if __name__ == "__main__":
    main()