from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

import crud.user
from core import security
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models.user import Token
from main import limiter, DEFAULT_LOGIN_LIMIT  # Import the limiter and rate limit

router = APIRouter()

@router.post("/api/auth/token", response_model=Token, tags=["auth"])
@limiter.limit(DEFAULT_LOGIN_LIMIT)  # Use configurable rate limit for login attempts
async def login_for_access_token(request: Request, db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = await crud.user.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
         
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Note on Logout: JWT is stateless. Logout is typically handled client-side
# by deleting the token. Server-side logout requires maintaining a token
# blacklist or using stateful sessions, which adds complexity. 