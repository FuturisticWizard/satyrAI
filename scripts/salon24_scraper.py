#!/usr/bin/env python3
"""
Salon24.pl Scraper - pobiera artykuły z polskich blogów prawicowych/libertariańskich
Szanuje robots.txt (1s delay) i pobiera treści z kategorii polityka, gospodarka.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

@dataclass
class BlogPost:
    """Struktura danych dla pojedynczego postu z bloga"""
    title: str
    author: str
    content: str
    url: str
    published_date: Optional[str] = None
    category: str = "unknown"
    blog_name: str = ""
    word_count: int = 0

class Salon24Scraper:
    def __init__(self, output_dir: str = "data/raw", rate_limit: float = 1.0):
        self.base_url = "http://www.salon24.pl"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit  # robots.txt wymaga 1s
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SatyrAI-Research/1.0; Educational research)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pl,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Konfiguracja kategorii do scrapowania
        self.categories = {
            "polityka": "/k/3,polityka",
            "gospodarka": "/k/4,gospodarka",
            "spoleczenstwo": "/k/6,spoleczenstwo"
        }
        
        self.setup_logging()

    def setup_logging(self):
        """Konfiguracja logowania"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('salon24_scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Pobiera stronę z respektowaniem rate limit"""
        try:
            time.sleep(self.rate_limit)  # Szanuj robots.txt
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Sprawdź encoding
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania {url}: {e}")
            return None

    def extract_blog_links_from_category(self, category_url: str) -> List[Dict[str, str]]:
        """Wyciąga linki do blogów z kategorii"""
        url = urljoin(self.base_url, category_url)
        soup = self.get_page(url)
        
        if not soup:
            return []
        
        blog_links = []
        
        # Szukaj różnych selektorów dla linków do blogów
        selectors = [
            'a[href*="/u/"]',  # linki do profili użytkowników
            'a[href*="/"]',     # ogólne linki
            '.blog-title a',   # tytuły blogów
            '.author-link',    # linki autorów
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Filtruj tylko linki do blogów użytkowników
                if '/u/' in href or '/blog/' in href:
                    blog_links.append({
                        'url': urljoin(self.base_url, href),
                        'text': text,
                        'type': 'user_blog'
                    })
        
        # Deduplikacja
        seen = set()
        unique_links = []
        for link in blog_links:
            url = link['url']
            if url not in seen and len(link['text']) > 3:
                seen.add(url)
                unique_links.append(link)
        
        self.logger.info(f"Znaleziono {len(unique_links)} linków do blogów w kategorii {category_url}")
        return unique_links

    def extract_posts_from_blog(self, blog_url: str, limit: int = 10) -> List[BlogPost]:
        """Wyciąga posty z indywidualnego bloga"""
        soup = self.get_page(blog_url)
        if not soup:
            return []
        
        posts = []
        
        # Różne selektory dla postów
        post_selectors = [
            'article',
            '.post',
            '.blog-post',
            '.entry',
            '[class*="post"]',
            '.tile'
        ]
        
        for selector in post_selectors:
            post_elements = soup.select(selector)
            
            if post_elements:
                self.logger.info(f"Znaleziono {len(post_elements)} postów używając selektora '{selector}'")
                
                for i, element in enumerate(post_elements[:limit]):
                    post = self.extract_post_content(element, blog_url)
                    if post and len(post.content) > 100:  # Minimum 100 znaków
                        posts.append(post)
                
                break  # Użyj pierwszy działający selektor
        
        return posts

    def extract_post_content(self, element, blog_url: str) -> Optional[BlogPost]:
        """Wyciąga treść z elementu postu"""
        try:
            # Tytuł
            title_selectors = ['h1', 'h2', 'h3', '.title', '[class*="title"]', 'a']
            title = ""
            for sel in title_selectors:
                title_elem = element.select_one(sel)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 10:  # Minimum sensowna długość tytułu
                        break
            
            if not title:
                return None
            
            # Autor (może być w różnych miejscach)
            author_selectors = ['.author', '.by', '[class*="author"]', '.username']
            author = ""
            for sel in author_selectors:
                author_elem = element.select_one(sel)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    break
            
            # Jeśli nie ma autora, wyciągnij z URL
            if not author:
                url_match = re.search(r'/u/([^/]+)', blog_url)
                if url_match:
                    author = url_match.group(1)
            
            # Treść
            content_selectors = ['.content', '.post-content', '.entry-content', 'p']
            content_parts = []
            
            for sel in content_selectors:
                content_elems = element.select(sel)
                if content_elems:
                    for elem in content_elems:
                        text = elem.get_text(strip=True)
                        if len(text) > 20:  # Pomijaj bardzo krótkie fragmenty
                            content_parts.append(text)
            
            # Jeśli nie znaleziono content selektorów, weź cały tekst z elementu
            if not content_parts:
                content_parts = [element.get_text(strip=True)]
            
            content = " ".join(content_parts)
            
            # Link do pełnego postu
            link_elem = element.select_one('a[href]')
            post_url = blog_url
            if link_elem:
                href = link_elem.get('href', '')
                if href.startswith('/'):
                    post_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    post_url = href
            
            # Data (opcjonalnie)
            date_selectors = ['.date', '.published', '[class*="date"]', 'time']
            published_date = None
            for sel in date_selectors:
                date_elem = element.select_one(sel)
                if date_elem:
                    published_date = date_elem.get_text(strip=True)
                    break
            
            post = BlogPost(
                title=title,
                author=author or "unknown",
                content=content,
                url=post_url,
                published_date=published_date,
                category="salon24",
                blog_name=blog_url.split('/')[-1] if '/' in blog_url else "unknown",
                word_count=len(content.split())
            )
            
            return post
            
        except Exception as e:
            self.logger.error(f"Błąd wyciągania postu: {e}")
            return None

    def save_posts(self, posts: List[BlogPost], filename: str):
        """Zapisuje posty do pliku JSONL"""
        output_path = self.output_dir / f"{filename}.jsonl"
        
        with output_path.open('a', encoding='utf-8') as f:
            for post in posts:
                record = {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": "salon24.pl",
                    "title": post.title,
                    "author": post.author,
                    "content": post.content,
                    "url": post.url,
                    "published_date": post.published_date,
                    "category": post.category,
                    "blog_name": post.blog_name,
                    "word_count": post.word_count,
                    "lang": "pl"
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        self.logger.info(f"Zapisano {len(posts)} postów do {output_path}")

    def run_category_scraping(self, category: str, max_blogs: int = 20, posts_per_blog: int = 5):
        """Uruchamia scraping dla danej kategorii"""
        self.logger.info(f"🚀 Rozpoczynam scraping kategorii: {category}")
        
        category_url = self.categories.get(category)
        if not category_url:
            self.logger.error(f"Nieznana kategoria: {category}")
            return
        
        # 1. Pobierz linki do blogów z kategorii
        blog_links = self.extract_blog_links_from_category(category_url)
        
        if not blog_links:
            self.logger.warning(f"Nie znaleziono blogów w kategorii {category}")
            return
        
        # 2. Ogranicz liczbę blogów
        blog_links = blog_links[:max_blogs]
        
        all_posts = []
        
        # 3. Iteruj przez blogi i pobierz posty
        for i, blog_link in enumerate(blog_links, 1):
            blog_url = blog_link['url']
            blog_name = blog_link['text']
            
            self.logger.info(f"📝 [{i}/{len(blog_links)}] Scraping blog: {blog_name} ({blog_url})")
            
            posts = self.extract_posts_from_blog(blog_url, limit=posts_per_blog)
            
            if posts:
                all_posts.extend(posts)
                self.logger.info(f"   ✅ Pobrano {len(posts)} postów")
            else:
                self.logger.warning(f"   ❌ Brak postów z {blog_url}")
        
        # 4. Zapisz wszystkie posty
        if all_posts:
            filename = f"salon24-{category}"
            self.save_posts(all_posts, filename)
            
            # Statystyki
            total_words = sum(post.word_count for post in all_posts)
            self.logger.info(f"📊 PODSUMOWANIE kategorii {category}:")
            self.logger.info(f"   Blogów przeskanowanych: {len(blog_links)}")
            self.logger.info(f"   Postów pobranych: {len(all_posts)}")
            self.logger.info(f"   Łączna liczba słów: {total_words:,}")
            self.logger.info(f"   Średnio słów na post: {total_words // len(all_posts) if all_posts else 0}")
        else:
            self.logger.warning(f"Brak postów do zapisania dla kategorii {category}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Salon24.pl Scraper')
    parser.add_argument('--category', choices=['polityka', 'gospodarka', 'spoleczenstwo', 'all'], 
                       default='polityka', help='Kategoria do scrapowania')
    parser.add_argument('--max-blogs', type=int, default=20, help='Maksymalna liczba blogów')
    parser.add_argument('--posts-per-blog', type=int, default=5, help='Posty na blog')
    parser.add_argument('--output-dir', default='data/raw', help='Folder wyjściowy')
    parser.add_argument('--rate-limit', type=float, default=1.5, help='Opóźnienie między requestami (s)')
    
    args = parser.parse_args()
    
    scraper = Salon24Scraper(output_dir=args.output_dir, rate_limit=args.rate_limit)
    
    if args.category == 'all':
        for category in scraper.categories.keys():
            scraper.run_category_scraping(category, args.max_blogs, args.posts_per_blog)
            print(f"\n{'='*60}\n")
    else:
        scraper.run_category_scraping(args.category, args.max_blogs, args.posts_per_blog)

if __name__ == "__main__":
    main()