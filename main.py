from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import database as db
import schemas as sch
import auth
import models
from datetime import datetime
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=db.engine)
    print("Таблицы базы данных созданы")
    yield

app = FastAPI(
    title="News Aggregator API",
    description="API для агрегации новостей с парсингом и категоризацией",
    version="1.0.0",
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request, db_session: Session = Depends(db.get_db)):
    news = db_session.query(models.NewsArticle).filter(
        models.NewsArticle.is_active == True
    ).order_by(models.NewsArticle.published_at.desc()).limit(20).all()
    return templates.TemplateResponse("news.html", {"request": request, "news": news})

@app.get("/create-news", response_class=HTMLResponse)
async def create_news_page(request: Request):
    return templates.TemplateResponse("create_news.html", {"request": request})

@app.get("/api/news/", response_model=List[sch.NewsArticle], summary="Получить все новости")
def read_news(skip: int = 0, limit: int = 100, db_session: Session = Depends(db.get_db)):
    """Получить список всех новостей с пагинацией"""
    return db_session.query(models.NewsArticle).filter(
        models.NewsArticle.is_active == True
    ).offset(skip).limit(limit).all()

@app.get("/api/news/{news_id}", response_model=sch.NewsArticle, summary="Получить новость по ID")
def read_news_item(news_id: int, db_session: Session = Depends(db.get_db)):
    """Получить конкретную новость по её ID"""
    news = db_session.query(models.NewsArticle).filter(models.NewsArticle.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    return news

@app.post("/api/news/", response_model=sch.NewsArticle, summary="Создать новость")
def create_news(news: sch.NewsArticleCreate, db_session: Session = Depends(db.get_db), 
                current_user: sch.User = Depends(auth.get_current_active_user)):
    """Создать новую новость (требуется аутентификация)"""
    db_news = models.NewsArticle(
        title=news.title,
        summary=news.summary,  
        source=news.source,
        category=news.category,
        url=news.url,
        published_at=news.published_at or datetime.now()
    )
    db_session.add(db_news)
    db_session.commit()
    db_session.refresh(db_news)
    return db_news

@app.put("/api/news/{news_id}", response_model=sch.NewsArticle, summary="Обновить новость")
def update_news(news_id: int, news: sch.NewsArticleUpdate, db_session: Session = Depends(db.get_db),
                current_user: sch.User = Depends(auth.get_current_active_user)):
    """Обновить существующую новость"""
    db_news = db_session.query(models.NewsArticle).filter(models.NewsArticle.id == news_id).first()
    if db_news is None:
        raise HTTPException(status_code=404, detail="News not found")
    
    update_data = news.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_news, field, value)
    
    db_session.commit()
    db_session.refresh(db_news)
    return db_news

@app.delete("/api/news/{news_id}", summary="Удалить новость")
def delete_news(news_id: int, db_session: Session = Depends(db.get_db),
                current_user: sch.User = Depends(auth.get_current_active_user)):
    """Удалить новость по ID"""
    news = db_session.query(models.NewsArticle).filter(models.NewsArticle.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    
    news.is_active = False
    db_session.commit()
    return {"message": "News deleted successfully"}

@app.post("/auth/register", response_model=sch.User, summary="Регистрация пользователя")
def register(user: sch.UserCreate, db_session: Session = Depends(db.get_db)):
    """Регистрация нового пользователя в системе"""
    if auth.get_user_by_email(db_session, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if auth.get_user_by_username(db_session, user.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    return auth.create_user(db_session, user)

@app.post("/auth/login", response_model=sch.Token, summary="Аутентификация пользователя")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db_session: Session = Depends(db.get_db)):
    """Аутентификация пользователя и получение JWT токена"""
    user = auth.authenticate_user(db_session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/parse-news/", summary="Парсинг тестовых новостей")
def parse_news(db_session: Session = Depends(db.get_db),
            current_user: sch.User = Depends(auth.get_current_active_user)):
    """Парсинг тестовых новостей из предопределенных источников"""
    sample_news = [
        {
            "title": "Новые технологии в IT",
            "summary": "Компании представляют инновационные решения в области искусственного интеллекта и машинного обучения.",
            "source": "TechNews",
            "category": "технологии",
            "url": "https://example.com/tech-news-1"
        },
        {
            "title": "Спортивные достижения", 
            "summary": "Спортсмены устанавливают новые рекорды на международных соревнованиях.",
            "source": "SportsDaily",
            "category": "спорт",
            "url": "https://example.com/sports-news-1"
        },
        {
            "title": "Экономические новости",
            "summary": "Центральный банк объявил о новых мерах по поддержке экономики.",
            "source": "FinanceTimes",
            "category": "экономика",
            "url": "https://example.com/economy-news-1"
        }
    ]
    
    added_count = 0
    for news_data in sample_news:
        existing = db_session.query(models.NewsArticle).filter(models.NewsArticle.url == news_data["url"]).first()
        if not existing:
            db_news = models.NewsArticle(
                title=news_data["title"],
                summary=news_data["summary"], 
                source=news_data["source"],
                category=news_data["category"],
                url=news_data["url"],
                published_at=datetime.now()
            )
            db_session.add(db_news)
            added_count += 1
    
    db_session.commit()
    return {"message": "News parsed successfully", "count": added_count}

@app.post("/api/parse-real-news/", summary="Парсинг реальных новостей из RSS")
def parse_real_news(db_session: Session = Depends(db.get_db),
                current_user: sch.User = Depends(auth.get_current_active_user)):
    """Парсинг реальных новостей из RSS источников"""
    try:
        from parser import RealNewsParser
        added_count = RealNewsParser.parse_real_rss_sources(db_session)
        return {
            "message": "Реальные новости успешно спарсены", 
            "count": added_count,
            "sources": ["Lenta.ru", "Ведомости", "Коммерсантъ", "ТАСС"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

@app.post("/api/update-categories/", summary="Обновление категорий новостей")
def update_categories(db_session: Session = Depends(db.get_db),
                    current_user: sch.User = Depends(auth.get_current_active_user)):
    """Автоматическое обновление категорий для существующих новостей"""
    try:
        from parser import RealNewsParser
        updated_count = RealNewsParser.update_news_categories(db_session)
        return {
            "message": "Категории успешно обновлены",
            "updated_count": updated_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обновления категорий: {str(e)}")

@app.get("/api/news/category/{category}", response_model=List[sch.NewsArticle], summary="Новости по категории")
def get_news_by_category(category: str, db_session: Session = Depends(db.get_db)):
    """Получить новости по определенной категории"""
    return db_session.query(models.NewsArticle).filter(
        models.NewsArticle.category == category,
        models.NewsArticle.is_active == True
    ).all()

@app.get("/api/personalized-news/", response_model=List[sch.NewsArticle], summary="Персонализированные новости")
def get_personalized_news(db_session: Session = Depends(db.get_db),
                        current_user: sch.User = Depends(auth.get_current_active_user)):
    """Получить персонализированную ленту новостей"""
    return db_session.query(models.NewsArticle).filter(
        models.NewsArticle.category == "технологии",
        models.NewsArticle.is_active == True
    ).limit(10).all()

@app.get("/api/health", summary="Проверка здоровья API")
def health_check(db_session: Session = Depends(db.get_db)):
    """Проверка статуса API и подключения к базе данных"""
    try:
        db_session.execute(text("SELECT 1"))
        news_count = db_session.query(models.NewsArticle).filter(models.NewsArticle.is_active == True).count()
        user_count = db_session.query(models.User).count()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "statistics": {
                "news_count": news_count,
                "user_count": user_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)