from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import Optional
import re

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match('^[a-zA-Z0-9_]+$', v):
            raise ValueError('Имя пользователя должно содержать только буквы, цифры и подчеркивания')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v

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