import requests
from bs4 import BeautifulSoup
import time
import random
import logging

def scrape_news_content(url):
    """
    Scrapes the main paragraph text from a given news URL.
    Includes a random delay and realistic User-Agent to avoid blocks.
    """
    logging.info(f"scrape_news_content called for url: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.google.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        # Human-like delay as requested
        time.sleep(random.uniform(1, 5))
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Yahoo finance articles typically store content in this class
        article_body = soup.find('div', class_='caas-body')
        if article_body:
            paragraphs = article_body.find_all('p')
        else:
            # Fallback for other sites
            paragraphs = soup.find_all('p')
            
        text = " ".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # Return up to 3000 characters to keep LLM context clean
        return text[:3000] if text else None
        
    except Exception as e:
        logging.warning(f"Failed to scrape {url}: {e}")
        return None
