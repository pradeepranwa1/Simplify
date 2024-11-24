import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext

from takehome.config import settings
from takehome.models import User, UserDetials


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Get tmp user from env database
def get_user_for_login(username: str) -> User:
    #this should be present in database
    if username==settings.TMP_USERNAME_FOR_AUTH:
        return User(username=username, hashed_password=settings.TMP_HASHED_PASSWORD_FOR_AUTH)
    else:
        return None

def authenticate_user(username: str, password: str):
    user = get_user_for_login(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.AUTH_ALGORITHM)
    return encoded_jwt

def get_user_details(username: str) -> UserDetials:
    #Add user details which are required for continuous usage
    return UserDetials(username=username)

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserDetials:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    return get_user_details(username)