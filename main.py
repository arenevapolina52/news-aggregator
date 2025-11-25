from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import database as db
import schemas as sch
import auth
from datetime import datetime
from parser import NewsParser, NEWS_SOURCES

app = FastAPI(
    title="News Aggregator API",
    description="API для агрегации новостей",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

templates = Jinja2Templates(directory="templates")

def get_news_articles(db_session: Session, skip: int = 0, limit: int = 100, category: Optional[str] = None):
    query = db_session.query(db.NewsArticle)
    if category:
        query = query.filter(db.NewsArticle.category == category)
    return query.offset(skip).limit(limit).all()

def get_news_article(db_session: Session, article_id: int):
    return db_session.query(db.NewsArticle).filter(db.NewsArticle.id == article_id).first()

def create_news_article(db_session: Session, article: sch.NewsArticleCreate):
    existing_article = db_session.query(db.NewsArticle).filter(
        db.NewsArticle.url == article.url
    ).first()
    
    if existing_article:
        raise HTTPException(
            status_code=400, 
            detail="Article with this URL already exists"
        )
    
    db_article = db.NewsArticle(**article.dict())
    db_session.add(db_article)
    db_session.commit()
    db_session.refresh(db_article)
    return db_article

def update_news_article(db_session: Session, article_id: int, article_update: sch.NewsArticleUpdate):
    db_article = get_news_article(db_session, article_id)
    if not db_article:
        return None
    
    update_data = article_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_article, field, value)
    
    db_session.commit()
    db_session.refresh(db_article)
    return db_article

def delete_news_article(db_session: Session, article_id: int):
    db_article = get_news_article(db_session, article_id)
    if not db_article:
        return None
    
    db_session.delete(db_article)
    db_session.commit()
    return db_article

async def get_current_user_from_request(request: Request, db_session: Session = Depends(db.get_db)):
    token = request.cookies.get("access_token")
    if token:
        try:
            user = await auth.get_current_user(token, db_session)
            return user
        except:
            return None
    return None

@app.post("/register", response_model=sch.User)
def register(user: sch.UserCreate, db_session: Session = Depends(db.get_db)):
    if auth.get_user_by_email(db_session, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    if auth.get_user_by_username(db_session, user.username):
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    
    return auth.create_user(db_session, user.dict())

@app.post("/login", response_model=sch.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: Session = Depends(db.get_db)
):
    user = auth.authenticate_user(db_session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db_session: Session = Depends(db.get_db)):
    current_user = await get_current_user_from_request(request, db_session)
    latest_news = get_news_articles(db_session, limit=6)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "current_user": current_user, "latest_news": latest_news}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/news", response_class=HTMLResponse)
async def news_page(request: Request, db_session: Session = Depends(db.get_db)):
    current_user = await get_current_user_from_request(request, db_session)
    articles = get_news_articles(db_session)
    return templates.TemplateResponse(
        "news.html",
        {"request": request, "current_user": current_user, "articles": articles}
    )

@app.get("/create-news", response_class=HTMLResponse)
async def create_news_page(request: Request, db_session: Session = Depends(db.get_db)):
    current_user = await get_current_user_from_request(request, db_session)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return templates.TemplateResponse(
        "create_news.html",
        {"request": request, "current_user": current_user}
    )

@app.get("/news/{article_id}", response_model=sch.NewsArticle)
def read_article(article_id: int, db_session: Session = Depends(db.get_db)):
    db_article = get_news_article(db_session, article_id)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return db_article

@app.post("/news/", response_model=sch.NewsArticle)
def create_article(
    article: sch.NewsArticleCreate,
    db_session: Session = Depends(db.get_db),
    current_user: sch.User = Depends(auth.get_current_active_user)
):
    return create_news_article(db_session, article)

@app.put("/news/{article_id}", response_model=sch.NewsArticle)
def update_article(
    article_id: int,
    article_update: sch.NewsArticleUpdate,
    db_session: Session = Depends(db.get_db),
    current_user: sch.User = Depends(auth.get_current_active_user)
):
    db_article = update_news_article(db_session, article_id, article_update)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return db_article

@app.delete("/news/{article_id}")
def delete_article(
    article_id: int,
    db_session: Session = Depends(db.get_db),
    current_user: sch.User = Depends(auth.get_current_active_user)
):
    db_article = delete_news_article(db_session, article_id)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Article deleted successfully"}

@app.get("/api/news")
async def api_get_news(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db_session: Session = Depends(db.get_db)
):
    articles = get_news_articles(db_session, skip=skip, limit=limit, category=category)
    return [
        {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "source": article.source,
            "category": article.category,
            "url": article.url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "created_at": article.created_at.isoformat() if article.created_at else None
        }
        for article in articles
    ]

@app.post("/api/parse-news")
async def parse_news_from_sources(db_session: Session = Depends(db.get_db)):
    parser = NewsParser()
    all_articles = []
    
    for source in NEWS_SOURCES:
        print(f"Парсим источник: {source}")
        articles = parser.parse_rss_feed(source)
        all_articles.extend(articles)
        
        for article_data in articles:
            try:
                existing = db_session.query(db.NewsArticle).filter(
                    db.NewsArticle.url == article_data["url"]
                ).first()
                
                if not existing:
                    news_article = sch.NewsArticleCreate(**article_data)
                    create_news_article(db_session, news_article)
            except Exception as e:
                print(f"Ошибка сохранения статьи: {e}")
                continue
    
    return {"message": f"Спаршено {len(all_articles)} новостей", "articles": all_articles}

@app.get("/api/personalized-news")
async def get_personalized_news(
    user_id: Optional[int] = None,
    db_session: Session = Depends(db.get_db)
):
    parser = NewsParser()
    all_articles = get_news_articles(db_session, limit=50)
    
    user_preferences = {
        "preferred_categories": ["technology", "science"],
        "preferred_sources": ["RSS Feed", "Lenta.ru"]
    }
    
    personalized_articles = parser.personalize_news(user_preferences, all_articles)
    
    return {
        "personalized_news": personalized_articles[:10],
        "user_preferences": user_preferences
    }

@app.get("/api/categories")
async def get_categories_stats(db_session: Session = Depends(db.get_db)):
    articles = get_news_articles(db_session)
    
    categories = {}
    for article in articles:
        category = article.category
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
    
    return {"categories": categories}

@app.get("/health")
def health_check(db_session: Session = Depends(db.get_db)):
    try:
        db_session.execute("SELECT 1")
        return {
            "status": "healthy", 
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database connection error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)