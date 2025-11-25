from sqlalchemy.orm import Session
import models
import schemas
from auth import get_password_hash, verify_password
from typing import List, Optional
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime

async def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

async def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

async def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

async def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def update_user_preferences(db: Session, user_id: int, preferences: schemas.UserPreferences):
    user = await get_user(db, user_id)
    if not user:
        return None
    
    user.preferred_categories.clear()
    
    if preferences.preferred_category_ids:
        categories = db.query(models.Category).filter(
            models.Category.id.in_(preferences.preferred_category_ids)
        ).all()
        user.preferred_categories.extend(categories)
    
    db.commit()
    db.refresh(user)
    return user

async def get_news(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.News).order_by(models.News.published_at.desc()).offset(skip).limit(limit).all()

async def get_news_by_id(db: Session, news_id: int):
    return db.query(models.News).filter(models.News.id == news_id).first()

async def get_personalized_news(db: Session, user_id: int, limit: int = 20, offset: int = 0):
    user = await get_user(db, user_id)
    if not user or not user.preferred_categories:
        return await get_news(db, skip=offset, limit=limit)
    
    preferred_category_ids = [cat.id for cat in user.preferred_categories]
    news = db.query(models.News).filter(
        models.News.category_id.in_(preferred_category_ids)
    ).order_by(models.News.published_at.desc()).offset(offset).limit(limit).all()
    
    return news

async def create_news(db: Session, news: schemas.NewsCreate):
    db_news = models.News(**news.dict())
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news

async def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()

async def get_category_by_id(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.id == category_id).first()

async def create_category(db: Session, category: schemas.CategoryCreate):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

async def get_sources(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Source).offset(skip).limit(limit).all()

async def get_source_by_id(db: Session, source_id: int):
    return db.query(models.Source).filter(models.Source.id == source_id).first()

async def create_source(db: Session, source: schemas.SourceCreate):
    db_source = models.Source(**source.dict())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

def categorize_text(text: str) -> str:
    categories = ['политика', 'технологии', 'спорт', 'наука', 'культура']
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['политика', 'правительство', 'выборы']):
        return 'политика'
    elif any(word in text_lower for word in ['технологии', 'искусственный интеллект', 'программирование']):
        return 'технологии'
    elif any(word in text_lower for word in ['спорт', 'футбол', 'хоккей']):
        return 'спорт'
    elif any(word in text_lower for word in ['наука', 'исследование', 'ученые']):
        return 'наука'
    else:
        return 'культура'

async def parse_yandex_news(db: Session):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://yandex.ru/news') as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_items = soup.find_all('div', class_='mg-card')[:10]
                    new_articles = []
                    
                    for item in news_items:
                        title_elem = item.find('h2') or item.find('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text().strip()
                        link = title_elem.get('href', '')
                        if link and not link.startswith('http'):
                            link = 'https://yandex.ru' + link
                        
                        content = title
                        category_name = categorize_text(content)
                        
                        category = db.query(models.Category).filter(
                            models.Category.name == category_name
                        ).first()
                        
                        if not category:
                            category = models.Category(name=category_name)
                            db.add(category)
                            db.commit()
                            db.refresh(category)
                        
                        source_name = "Яндекс.Новости"
                        source = db.query(models.Source).filter(
                            models.Source.name == source_name
                        ).first()
                        
                        if not source:
                            source = models.Source(
                                name=source_name,
                                url="https://yandex.ru/news",
                                rss_feed=""
                            )
                            db.add(source)
                            db.commit()
                            db.refresh(source)
                        
                        existing = db.query(models.News).filter(models.News.url == link).first()
                        if existing:
                            continue
                        
                        news_data = {
                            "title": title,
                            "content": content,
                            "url": link,
                            "published_at": datetime.now(),
                            "source_id": source.id,
                            "category_id": category.id
                        }
                        
                        db_news = models.News(**news_data)
                        db.add(db_news)
                        new_articles.append(db_news)
                    
                    db.commit()
                    return new_articles
                    
    except Exception as e:
        print(f"Error parsing Yandex: {e}")
        return []

async def parse_wikipedia_news(db: Session):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://ru.wikipedia.org/wiki/%D0%97%D0%B0%D0%B3%D0%BB%D0%B0%D0%B2%D0%BD%D0%B0%D1%8F_%D1%81%D1%82%D1%80%D0%B0%D0%BD%D0%B8%D1%86%D0%B0') as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    news_section = soup.find('div', id='main-tfa')
                    if not news_section:
                        return []
                    
                    news_items = news_section.find_all('p')[:5]
                    new_articles = []
                    
                    for item in news_items:
                        text = item.get_text().strip()
                        if len(text) < 50:
                            continue
                            
                        title = text[:100] + "..."
                        content = text
                        category_name = categorize_text(content)
                        
                        category = db.query(models.Category).filter(
                            models.Category.name == category_name
                        ).first()
                        
                        if not category:
                            category = models.Category(name=category_name)
                            db.add(category)
                            db.commit()
                            db.refresh(category)
                        
                        source_name = "Википедия"
                        source = db.query(models.Source).filter(
                            models.Source.name == source_name
                        ).first()
                        
                        if not source:
                            source = models.Source(
                                name=source_name,
                                url="https://ru.wikipedia.org",
                                rss_feed=""
                            )
                            db.add(source)
                            db.commit()
                            db.refresh(source)
                        
                        url = "https://ru.wikipedia.org/wiki/" + title.replace(' ', '_')
                        existing = db.query(models.News).filter(models.News.url == url).first()
                        if existing:
                            continue
                        
                        news_data = {
                            "title": title,
                            "content": content,
                            "url": url,
                            "published_at": datetime.now(),
                            "source_id": source.id,
                            "category_id": category.id
                        }
                        
                        db_news = models.News(**news_data)
                        db.add(db_news)
                        new_articles.append(db_news)
                    
                    db.commit()
                    return new_articles
                    
    except Exception as e:
        print(f"Error parsing Wikipedia: {e}")
        return []

async def parse_real_news(db: Session):
    yandex_articles = await parse_yandex_news(db)
    wikipedia_articles = await parse_wikipedia_news(db)
    return yandex_articles + wikipedia_articles