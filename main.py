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

app = FastAPI(
    title="News Aggregator API",
    description="API для агрегации новостей с парсингом и категоризацией",
    version="1.0.0"
)

templates = Jinja2Templates(directory="templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=db.engine)
    print("✅ Таблицы базы данных созданы")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/news-page", response_class=HTMLResponse)
async def news_page(request: Request, db: Session = Depends(db.get_db)):
    news = db.query(models.News).order_by(models.News.published_at.desc()).limit(20).all()
    return templates.TemplateResponse("news.html", {"request": request, "news": news})

@app.get("/create-news-page", response_class=HTMLResponse)
async def create_news_page(request: Request):
    return templates.TemplateResponse("create_news.html", {"request": request})

@app.get("/api/news/", response_model=List[sch.NewsArticle])
def read_news(skip: int = 0, limit: int = 100, db: Session = Depends(db.get_db)):
    news_items = db.query(models.News).offset(skip).limit(limit).all()
    result = []
    for item in news_items:
        # Получаем название источника и категории через отношения
        source_name = item.source_rel.name if item.source_rel else "Неизвестно"
        category_name = item.category.name if item.category else "Неизвестно"
        
        result.append(sch.NewsArticle(
            id=item.id,
            title=item.title,
            content=item.content,
            source=source_name,
            category=category_name,
            url=item.url,
            published_at=item.published_at,
            created_at=item.created_at
        ))
    return result

@app.get("/api/news/{news_id}", response_model=sch.NewsArticle)
def read_news_item(news_id: int, db: Session = Depends(db.get_db)):
    news = db.query(models.News).filter(models.News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    
    source_name = news.source_rel.name if news.source_rel else "Неизвестно"
    category_name = news.category.name if news.category else "Неизвестно"
    
    return sch.NewsArticle(
        id=news.id,
        title=news.title,
        content=news.content,
        source=source_name,
        category=category_name,
        url=news.url,
        published_at=news.published_at,
        created_at=news.created_at
    )

@app.post("/api/news/", response_model=sch.NewsArticle)
def create_news(news: sch.NewsArticleCreate, db: Session = Depends(db.get_db), 
                current_user: sch.User = Depends(auth.get_current_active_user)):
    # Находим или создаем категорию
    category = db.query(models.Category).filter(models.Category.name == news.category).first()
    if not category:
        category = models.Category(name=news.category)
        db.add(category)
        db.commit()
        db.refresh(category)
    
    # Находим или создаем источник
    source_obj = db.query(models.Source).filter(models.Source.name == news.source).first()
    if not source_obj:
        source_obj = models.Source(name=news.source, url="")
        db.add(source_obj)
        db.commit()
        db.refresh(source_obj)
    
    # Создаем новость с правильными полями
    db_news = models.News(
        title=news.title,
        content=news.content,
        url=news.url,
        published_at=news.published_at,
        category_id=category.id,
        source_id=source_obj.id
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    
    return sch.NewsArticle(
        id=db_news.id,
        title=db_news.title,
        content=db_news.content,
        source=news.source,
        category=news.category,
        url=db_news.url,
        published_at=db_news.published_at,
        created_at=db_news.created_at
    )

@app.put("/api/news/{news_id}", response_model=sch.NewsArticle)
def update_news(news_id: int, news: sch.NewsArticleUpdate, db: Session = Depends(db.get_db),
                current_user: sch.User = Depends(auth.get_current_active_user)):
    db_news = db.query(models.News).filter(models.News.id == news_id).first()
    if db_news is None:
        raise HTTPException(status_code=404, detail="News not found")
    
    update_data = news.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_news, field, value)
    
    db.commit()
    db.refresh(db_news)
    
    source_name = db_news.source_rel.name if db_news.source_rel else "Неизвестно"
    category_name = db_news.category.name if db_news.category else "Неизвестно"
    
    return sch.NewsArticle(
        id=db_news.id,
        title=db_news.title,
        content=db_news.content,
        source=source_name,
        category=category_name,
        url=db_news.url,
        published_at=db_news.published_at,
        created_at=db_news.created_at
    )

@app.delete("/api/news/{news_id}")
def delete_news(news_id: int, db: Session = Depends(db.get_db),
                current_user: sch.User = Depends(auth.get_current_active_user)):
    news = db.query(models.News).filter(models.News.id == news_id).first()
    if news is None:
        raise HTTPException(status_code=404, detail="News not found")
    
    db.delete(news)
    db.commit()
    return {"message": "News deleted successfully"}

@app.post("/api/register", response_model=sch.User)
def register(user: sch.UserCreate, db: Session = Depends(db.get_db)):
    if auth.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if auth.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    return auth.create_user(db, user)

@app.post("/api/login", response_model=sch.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(db.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/parse-news/")
def parse_news(db: Session = Depends(db.get_db),
               current_user: sch.User = Depends(auth.get_current_active_user)):
    import parser
    articles = parser.parse_real_news(db)
    return {"message": "News parsed successfully", "count": len(articles)}

@app.get("/api/news/category/{category}", response_model=List[sch.NewsArticle])
def get_news_by_category(category: str, db: Session = Depends(db.get_db)):
    news_items = db.query(models.News).join(models.Category).filter(models.Category.name == category).all()
    result = []
    for item in news_items:
        source_name = item.source_rel.name if item.source_rel else "Неизвестно"
        result.append(sch.NewsArticle(
            id=item.id,
            title=item.title,
            content=item.content,
            source=source_name,
            category=category,
            url=item.url,
            published_at=item.published_at,
            created_at=item.created_at
        ))
    return result

@app.get("/api/personalized-news/", response_model=List[sch.NewsArticle])
def get_personalized_news(db: Session = Depends(db.get_db),
                        current_user: sch.User = Depends(auth.get_current_active_user)):
    news_items = db.query(models.News).order_by(models.News.published_at.desc()).limit(20).all()
    result = []
    for item in news_items:
        source_name = item.source_rel.name if item.source_rel else "Неизвестно"
        category_name = item.category.name if item.category else "Неизвестно"
        result.append(sch.NewsArticle(
            id=item.id,
            title=item.title,
            content=item.content,
            source=source_name,
            category=category_name,
            url=item.url,
            published_at=item.published_at,
            created_at=item.created_at
        ))
    return result

@app.get("/api/health")
def health_check(db: Session = Depends(db.get_db)):
    try:
        db.execute(text("SELECT 1"))
        
        news_count = db.query(models.News).count()
        user_count = db.query(models.User).count()
        category_count = db.query(models.Category).count()
        source_count = db.query(models.Source).count()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "statistics": {
                "news_count": news_count,
                "user_count": user_count,
                "category_count": category_count,
                "source_count": source_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)