import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List, Dict
import database as db
from sqlalchemy.orm import Session

class NewsParser:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
    def parse_rss_feed(self, rss_url: str) -> List[Dict]:
        try:
            response = requests.get(rss_url, headers={"User-Agent": self.user_agent})
            soup = BeautifulSoup(response.content, 'xml')
            
            articles = []
            for item in soup.find_all('item')[:10]:
                title = item.title.text if item.title else "Без заголовка"
                description = item.description.text if item.description else ""
                link = item.link.text if item.link else ""
                pub_date = item.pubDate.text if item.pubDate else datetime.now().isoformat()
                
                category = self.categorize_article(title + " " + description)
                
                articles.append({
                    "title": title,
                    "content": description,
                    "source": "RSS Feed",
                    "category": category,
                    "url": link,
                    "published_at": pub_date
                })
            return articles
        except Exception as e:
            print(f"Ошибка парсинга RSS: {e}")
            return []
    
    def parse_news_site(self, url: str) -> List[Dict]:
        try:
            response = requests.get(url, headers={"User-Agent": self.user_agent})
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            news_elements = soup.find_all(['h1', 'h2', 'h3'], class_=re.compile(r'title|header|news'))
            
            for element in news_elements[:5]:
                title = element.get_text().strip()
                if len(title) > 10:
                    category = self.categorize_article(title)
                    
                    articles.append({
                        "title": title,
                        "content": f"Новость с сайта {url}",
                        "source": url,
                        "category": category,
                        "url": url,
                        "published_at": datetime.now().isoformat()
                    })
            return articles
        except Exception as e:
            print(f"Ошибка парсинга сайта: {e}")
            return []
    
    def categorize_article(self, text: str) -> str:
        text = text.lower()
        
        categories = {
            "technology": ["искусственный интеллект", "ai", "технологи", "гаджет", "смартфон", "компьютер", "программ", "it"],
            "politics": ["политик", "правительств", "президент", "выбор", "закон", "парламент", "министр"],
            "sports": ["спорт", "футбол", "хоккей", "баскетбол", "чемпионат", "матч", "игрок", "тренер"],
            "entertainment": ["кино", "фильм", "сериал", "музык", "знаменитост", "развлечен", "актер"],
            "science": ["наук", "исследован", "учен", "открытие", "космос", "медицин", "биолог"],
            "business": ["бизнес", "экономик", "финанс", "рынок", "компани", "инвест", "доллар", "рубль"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "other"
    
    def personalize_news(self, user_preferences: Dict, articles: List[Dict]) -> List[Dict]:
        if not user_preferences:
            return articles
        
        preferred_categories = user_preferences.get("preferred_categories", [])
        preferred_sources = user_preferences.get("preferred_sources", [])
        
        personalized_articles = []
        
        for article in articles:
            score = 0
            
            if article["category"] in preferred_categories:
                score += 2
            
            if any(source.lower() in article["source"].lower() for source in preferred_sources):
                score += 1
            
            article["personalization_score"] = score
            personalized_articles.append(article)
        
        personalized_articles.sort(key=lambda x: x["personalization_score"], reverse=True)
        return personalized_articles

NEWS_SOURCES = [
    "https://lenta.ru/rss/news",
    "https://www.vedomosti.ru/rss/news",
    "https://www.kommersant.ru/RSS/news.xml"
]