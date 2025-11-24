from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional
import re

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match('^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password')
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

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