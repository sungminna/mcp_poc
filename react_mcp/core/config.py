import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# --- JWT Settings ---
# Generate a secret key using: openssl rand -hex 32
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_needs_to_be_changed")
ALGORITHM = "HS256"
# Access token expires in 30 minutes
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# --- Database Settings ---
# Default assumes DB is running on localhost if app is outside Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/fastapi_db") 