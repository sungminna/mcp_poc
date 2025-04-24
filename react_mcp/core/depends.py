from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from langfuse.callback import CallbackHandler
import jwt

from core.config import SECRET_KEY, ALGORITHM, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

# Rate limiter using IP by default; can be used for all endpoints
limiter = Limiter(key_func=get_remote_address)

# Custom rate-limit key: uses JWT 'sub' claim for authenticated users, falls back to IP
async def get_user_id_from_token(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return get_remote_address(request)
    token = auth_header.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass
    return get_remote_address(request)

# Langfuse callback handler for tracing
langfuse_handler = CallbackHandler(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST,
)

# Database dependency and security dependencies
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from core.security import get_current_user, get_current_active_user 