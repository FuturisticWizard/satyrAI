"""
Test nowych RSS feeds z Fazy 1 przed pełnym scrapowaniem.
"""
import requests
import time
import feedparser
from urllib.robotparser import RobotFileParser

# FAZA 2 - Nowe feedy do przetestowania
NEW_FEEDS = [
    {
        "name": "wPolityce.pl",
        "url": "https://wpolityce.pl/rss",
        "robots_url": "https://wpolityce.pl/robots.txt"
    },
    {
        "name": "Not The Bee", 
        "url": "https://notthebee.com/rss",
        "robots_url": "https://notthebee.com/robots.txt"
    },
    {
        "name": "Fraser Institute",
        "url": "https://www.fraserinstitute.org/rss-feeds",
        "robots_url": "https://www.fraserinstitute.org/robots.txt"
    },
    {
        "name": "Legal Insurrection",
        "url": "https://legalinsurrection.com/feed/",
        "robots_url": "https://legalinsurrection.com/robots.txt"
    }
]

def test_robots_txt(robots_url):
    """Test czy robots.txt pozwala na crawling."""
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        can_fetch = rp.can_fetch("SatyrAI-bot", "/")
        return can_fetch, "OK"
    except Exception as e:
        return False, str(e)

def test_rss_feed(feed_url):
    """Test czy RSS feed jest dostępny i ma content."""
    try:
        headers = {
            'User-Agent': 'SatyrAI-bot/0.1 (https://github.com/your-repo)'
        }
        response = requests.get(feed_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", 0
        
        # Parse RSS
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
            return False, f"Parse error: {feed.bozo_exception}", 0
        
        entries = len(feed.entries)
        if entries == 0:
            return False, "No entries found", 0
        
        # Sprawdź czy mamy tytuły i contennt
        sample_entry = feed.entries[0]
        has_content = bool(sample_entry.get('summary') or sample_entry.get('content'))
        
        return True, f"OK - {entries} entries", entries
        
    except Exception as e:
        return False, str(e), 0

def main():
    """Test wszystkich nowych feedów."""
    print("=== TEST NOWYCH RSS FEEDS - FAZA 2 ===\n")
    
    results = []
    
    for feed_info in NEW_FEEDS:
        print(f"Testing: {feed_info['name']}")
        print(f"URL: {feed_info['url']}")
        
        # Test robots.txt
        robots_allowed, robots_msg = test_robots_txt(feed_info['robots_url'])
        print(f"  Robots.txt: {'✅' if robots_allowed else '❌'} {robots_msg}")
        
        # Test RSS feed
        feed_ok, feed_msg, entry_count = test_rss_feed(feed_info['url'])
        print(f"  RSS Feed: {'✅' if feed_ok else '❌'} {feed_msg}")
        
        results.append({
            'name': feed_info['name'],
            'robots_ok': robots_allowed,
            'feed_ok': feed_ok,
            'entries': entry_count
        })
        
        print()
        time.sleep(1)  # Rate limiting
    
    # Podsumowanie
    print("=== PODSUMOWANIE ===")
    working_feeds = [r for r in results if r['feed_ok']]
    total_entries = sum(r['entries'] for r in working_feeds)
    
    print(f"Działające feedy: {len(working_feeds)}/{len(NEW_FEEDS)}")
    print(f"Potencjalne nowe artykuły: ~{total_entries}")
    
    print("\n--- Status per feed ---")
    for r in results:
        status = "✅" if r['feed_ok'] else "❌"
        print(f"{status} {r['name']}: {r['entries']} entries")
    
    if working_feeds:
        print(f"\n🚀 Ready to scrape {len(working_feeds)} new sources!")
    else:
        print("\n⚠️  No working feeds found")

if __name__ == "__main__":
    main()