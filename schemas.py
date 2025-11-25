from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

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

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True

class SourceBase(BaseModel):
    name: str
    url: str
    rss_feed: Optional[str] = None

class SourceCreate(SourceBase):
    pass

class Source(SourceBase):
    id: int
    class Config:
        from_attributes = True

class NewsBase(BaseModel):
    title: str
    content: str
    url: str
    published_at: datetime
    source_id: int
    category_id: Optional[int] = None

class NewsCreate(NewsBase):
    pass

class News(NewsBase):
    id: int
    category: Optional[Category] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserPreferences(BaseModel):
    preferred_category_ids: List[int]