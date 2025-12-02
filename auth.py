from sqlalchemy.orm import Session
from sqlalchemy import or_
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

import models
import schemas
from database import get_db

SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------------------------------------------------------
#              BCRYPT FUNCTIONS (only bcrypt)
# ---------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    # bcrypt has limit of 72 bytes → truncate to avoid ValueError
    password_bytes = password.encode("utf-8")[:72]

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify hashed password."""
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ---------------------------------------------------------
#                    USER FUNCTIONS
# ---------------------------------------------------------

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def authenticate_user(db: Session, username_or_email: str, password: str):
    """Authenticate by username OR email."""
    user = (
        db.query(models.User)
        .filter(
            or_(
                models.User.username == username_or_email,
                models.User.email == username_or_email,
            )
        )
        .first()
    )

    if not user:
        return False

    if not verify_password(password, user.hashed_password):
        return False

    return user


def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user with bcrypt hashing."""

    hashed_password = hash_password(user.password)

    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        is_active=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ---------------------------------------------------------
#                    JWT TOKEN FUNCTIONS
# ---------------------------------------------------------

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generate JWT token."""
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------
#                    CURRENT USER DEPENDS
# ---------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, username)

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: schemas.User = Depends(get_current_user)
):
    """Check if user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return current_user
