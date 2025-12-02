import aiohttp
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import random
from models import NewsArticle
import requests
import feedparser

logger = logging.getLogger(__name__)

class NewsParser:
    
    CATEGORIES = ["политика", "технологии", "спорт", "развлечения", "наука", "экономика", "культура"]
    SOURCES = ["РИА Новости", "Коммерсантъ", "ТАСС", "Интерфакс", "РБК", "Ведомости", "Газета.Ru"]
    
    @staticmethod
    def parse_news(db: Session, count: int = 10):
        """Парсинг новостей - генерация тестовых данных"""
        try:
            logger.info("Starting news parsing...")
            NewsParser.generate_sample_news(db, count)
            logger.info("News parsing completed successfully")
        except Exception as e:
            logger.error(f"Error parsing news: {e}")
            raise
    
    @staticmethod
    def generate_sample_news(db: Session, count: int = 10):
        """Генерация тестовых новостей"""
        sample_titles = [
            "Важное политическое событие состоялось сегодня",
            "Новые технологии меняют мир",
            "Спортивные достижения поражают воображение",
            "Культурные мероприятия привлекают тысячи зрителей",
            "Научное открытие может изменить будущее",
            "Экономические показатели демонстрируют рост",
            "Международные отношения развиваются",
            "Инновации в медицине спасают жизни",
            "Образовательные реформы и их последствия",
            "Экологические инициативы набирают популярность"
        ]
        
        sample_summaries = [
            "Это важное событие повлияет на будущее развитие региона.",
            "Технологический прорыв открывает новые возможности для бизнеса.",
            "Спортсмены установили новый рекорд в сложных условиях.",
            "Культурное событие собрало участников со всего мира.",
            "Ученые сделали открытие, которое может решить глобальные проблемы.",
            "Экономический рост свидетельствует о восстановлении после кризиса.",
            "Дипломатические усилия приносят свои плоды.",
            "Медицинские исследования открывают новые методы лечения.",
            "Реформы в образовании направлены на улучшение качества обучения.",
            "Экологические проекты получают поддержку на международном уровне."
        ]
        
        for i in range(count):
            category = random.choice(NewsParser.CATEGORIES)
            source = random.choice(NewsParser.SOURCES)
            
            existing = db.query(NewsArticle).filter(
                NewsArticle.title == sample_titles[i]
            ).first()
            
            if not existing:
                article = NewsArticle(
                    title=sample_titles[i],
                    summary=sample_summaries[i],
                    url=f"https://example.com/news/{i}",
                    source=source,
                    category=category,
                    published_at=datetime.now()
                )
                db.add(article)
        
        db.commit()
        logger.info(f"Generated {count} sample news articles")
    
    @staticmethod
    def get_personalized_news(db: Session, user_id: int, limit: int = 20):
        """Получение персонализированных новостей на основе предпочтений пользователя"""
        from models import UserPreference
        
        preferences = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()
        
        query = db.query(NewsArticle).filter(NewsArticle.is_active == True)
        
        if preferences:
            categories = [pref.category for pref in preferences if pref.category]
            if categories:
                query = query.filter(NewsArticle.category.in_(categories))
        
        return query.order_by(NewsArticle.published_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_news_categories(db: Session):
        """Получение списка всех категорий"""
        categories = db.query(NewsArticle.category).distinct().filter(
            NewsArticle.category.isnot(None),
            NewsArticle.is_active == True
        ).all()
        return [row[0] for row in categories if row[0]]
    
    @staticmethod
    def get_news_sources(db: Session):
        """Получение списка всех источников"""
        sources = db.query(NewsArticle.source).distinct().filter(NewsArticle.is_active == True).all()
        return [row[0] for row in sources if row[0]]


class RealNewsParser:
    """Реальный парсер новостей из RSS источников"""
    
    @staticmethod
    def parse_real_rss_sources(db: Session):
        """Парсинг реальных RSS лент"""
        rss_sources = [
            {"url": "https://lenta.ru/rss/news", "source": "Lenta.ru", "category": "общее"},
            {"url": "https://www.vedomosti.ru/rss/news", "source": "Ведомости", "category": "экономика"},
            {"url": "https://www.kommersant.ru/RSS/news.xml", "source": "Коммерсантъ", "category": "политика"},
            {"url": "https://tass.ru/rss/v2.xml", "source": "ТАСС", "category": "общее"},
        ]
        
        added_count = 0
        for source in rss_sources:
            try:
                print(f"🔍 Парсинг источника: {source['source']}")
                feed = feedparser.parse(source["url"])
                
                for entry in feed.entries[:5]:  
                    if not db.query(NewsArticle).filter(NewsArticle.url == entry.link).first():
                        
                        summary_text = entry.summary if hasattr(entry, 'summary') else (entry.description if hasattr(entry, 'description') else entry.title)
                        category = RealNewsParser.detect_category(entry.title, summary_text)
                        
                        article = NewsArticle(
                            title=entry.title[:200], 
                            summary=summary_text[:500],
                            url=entry.link,
                            source=source["source"],
                            category=category or source["category"],
                            published_at=datetime.now()
                        )
                        db.add(article)
                        added_count += 1
                        print(f"✅ Добавлена новость: {entry.title[:50]}...")
                        
            except Exception as e:
                print(f"❌ Ошибка парсинга {source['source']}: {e}")
        
        db.commit()
        print(f"🎉 Парсинг завершен. Добавлено {added_count} новостей")
        return added_count
    
    @staticmethod
    def detect_category(title: str, summary: str) -> str:
        """Определение категории на основе содержимого"""
        text = (title + " " + summary).lower()
        
        category_keywords = {
            "технологии": ["ии", "искусственный интеллект", "программирование", "гаджет", "смартфон", "it", "цифровой", "технологи", "компьютер"],
            "политика": ["путин", "правительство", "выборы", "парламент", "министр", "санкции", "международный", "политик", "государство"],
            "экономика": ["рубль", "доллар", "биржа", "инфляция", "бизнес", "компания", "рынок", "экономика", "финанс", "банк", "инвестиц"],
            "спорт": ["футбол", "хоккей", "чемпионат", "сборная", "матч", "игрок", "спорт", "соревнован", "олимпийск"],
            "наука": ["исследование", "ученые", "открытие", "космос", "медицина", "наука", "изобретение", "лаборатор"],
            "культура": ["кино", "фильм", "музыка", "концерт", "выставка", "театр", "культура", "искусство", "артист"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return "общее"

    @staticmethod
    def update_news_categories(db: Session):
        """Обновление категорий для существующих новостей"""
        articles = db.query(NewsArticle).filter(NewsArticle.category == None).all()
        
        updated_count = 0
        for article in articles:
            new_category = RealNewsParser.detect_category(article.title, article.summary)
            if new_category:
                article.category = new_category
                updated_count += 1
        
        db.commit()
        print(f"🔄 Обновлено категорий: {updated_count}")
        return updated_count