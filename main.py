from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import crud, models, schemas
from database import SessionLocal, engine
from auth import create_access_token, get_current_user, verify_password
from typing import List

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="News Aggregator API",
    description="News aggregator with parsing from Yandex and Wikipedia",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await crud.create_user(db=db, user=user)

@app.post("/login")
async def login(form_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = await crud.get_user_by_email(db, email=form_data.email)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/news/", response_model=List[schemas.News])
async def read_news(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    news = await crud.get_news(db, skip=skip, limit=limit)
    return news

@app.get("/news/personalized/", response_model=List[schemas.News])
async def read_personalized_news(
    skip: int = 0, 
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    news = await crud.get_personalized_news(db, user_id=current_user.id, limit=limit, offset=skip)
    return news

@app.post("/news/", response_model=schemas.News)
async def create_news_item(
    news: schemas.NewsCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await crud.create_news(db=db, news=news)

@app.get("/news/{news_id}", response_model=schemas.News)
async def read_news_item(news_id: int, db: Session = Depends(get_db)):
    db_news = await crud.get_news_by_id(db, news_id=news_id)
    if db_news is None:
        raise HTTPException(status_code=404, detail="News not found")
    return db_news

@app.get("/categories/", response_model=List[schemas.Category])
async def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categories = await crud.get_categories(db, skip=skip, limit=limit)
    return categories

@app.post("/categories/", response_model=schemas.Category)
async def create_category(
    category: schemas.CategoryCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await crud.create_category(db=db, category=category)

@app.get("/sources/", response_model=List[schemas.Source])
async def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sources = await crud.get_sources(db, skip=skip, limit=limit)
    return sources

@app.post("/sources/", response_model=schemas.Source)
async def create_source(
    source: schemas.SourceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await crud.create_source(db=db, source=source)

@app.get("/user/preferences", response_model=schemas.UserPreferences)
async def get_user_preferences(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preferred_category_ids = [cat.id for cat in current_user.preferred_categories]
    return schemas.UserPreferences(preferred_category_ids=preferred_category_ids)

@app.put("/user/preferences", response_model=schemas.User)
async def update_user_preferences(
    preferences: schemas.UserPreferences,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await crud.update_user_preferences(db, current_user.id, preferences)

@app.post("/parse-news/")
async def parse_news(
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    background_tasks.add_task(crud.parse_real_news, db)
    return {"message": "News parsing started"}

@app.get("/")
async def root():
    return {"message": "News Aggregator API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}