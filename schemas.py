from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class NewsArticleBase(BaseModel):
    title: str
    content: str
    source: str
    category: str
    url: str
    published_at: datetime

class NewsArticleCreate(NewsArticleBase):
    pass

class NewsArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None

class NewsArticle(NewsArticleBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True