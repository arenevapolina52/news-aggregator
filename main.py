from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import database as db
import schemas as sch
import auth
from datetime import datetime

app = FastAPI(
    title="News Aggregator API",
    description="API для агрегации новостей с парсингом, категоризацией и персонализацией",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def get_news_articles(
    db_session: Session, 
    skip: int = 0, 
    limit: int = 100,
    category: Optional[str] = None
):
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

def update_news_article(
    db_session: Session, 
    article_id: int, 
    article_update: sch.NewsArticleUpdate
):
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

@app.post("/register", response_model=sch.User, summary="Регистрация пользователя")
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

@app.post("/login", response_model=sch.Token, summary="Аутентификация пользователя")
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

@app.get("/", summary="Главная страница")
def read_root():
    return {"message": "Welcome to News Aggregator API"}

@app.get("/news/", response_model=List[sch.NewsArticle], summary="Получить все новости")
def read_articles(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db_session: Session = Depends(db.get_db)
):
    articles = get_news_articles(db_session, skip=skip, limit=limit, category=category)
    return articles

@app.get("/news/{article_id}", response_model=sch.NewsArticle, summary="Получить новость по ID")
def read_article(article_id: int, db_session: Session = Depends(db.get_db)):
    db_article = get_news_article(db_session, article_id)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return db_article

@app.post("/news/", response_model=sch.NewsArticle, summary="Создать новую статью")
def create_article(
    article: sch.NewsArticleCreate,
    db_session: Session = Depends(db.get_db),
    current_user: sch.User = Depends(auth.get_current_active_user)
):
    return create_news_article(db_session, article)

@app.put("/news/{article_id}", response_model=sch.NewsArticle, summary="Обновить статью")
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

@app.delete("/news/{article_id}", summary="Удалить статью")
def delete_article(
    article_id: int,
    db_session: Session = Depends(db.get_db),
    current_user: sch.User = Depends(auth.get_current_active_user)
):
    db_article = delete_news_article(db_session, article_id)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Article deleted successfully"}

@app.get("/health", summary="Проверка здоровья API")
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