"""Main application module: configures FastAPI app with lifecycle events, database schema initialization, graph and vector services setup, rate limiting, CORS, and API routers."""
from fastapi import FastAPI, Depends, Request
from dotenv import load_dotenv
from contextlib import asynccontextmanager  # Async context manager for application lifespan
import logging  # Logging facility for application events
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import jwt

from database import engine, Base, get_db # Import database engine, Base, and get_db
from models import user as user_model # Import user model to create table
from services.neo4j_service import neo4j_service # Import the Neo4j service instance
from services.milvus_service import milvus_service # Import the Milvus service instance

from langfuse.callback import CallbackHandler
import os

import models.chat  # Register chat models so their tables are created

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Rate limiting configuration using environment variables with sensible defaults
DEFAULT_CHAT_LIMIT = os.getenv("RATE_LIMIT_CHAT", "30/minute")
DEFAULT_LOGIN_LIMIT = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
DEFAULT_REGISTER_LIMIT = os.getenv("RATE_LIMIT_REGISTER", "5/hour")

# JWT secret key for signing and verifying tokens
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_needs_to_be_changed")

# Custom key function for chat endpoint based on user token
def get_user_id_from_token(request: Request):
    # Determine rate limiter key: use JWT subject or fallback to client IP
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # Fallback to IP when Authorization header is missing or invalid
        return get_remote_address(request)
            
    token = auth_header.replace("Bearer ", "")
    
    # Decode JWT token to get user ID
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("sub")  # 'sub' typically contains the username or user ID
    
    if user_id:
        logger.debug(f"Rate limiting based on user: {user_id}")
        return f"user:{user_id}"
    else:
        # Fall back to IP if token doesn't contain user ID
        return get_remote_address(request)

# Initialize rate limiter with IP-based key function
limiter = Limiter(key_func=get_remote_address)

# Async function to ensure database schema at startup
async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema ensured.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup and shutdown lifecycle
    logger.info("Starting application...")
    try:
        # Initialize database, graph, and vector services
        
        # Create database tables asynchronously
        await create_db_tables()

        # Connect to Neo4j and create constraints/indexes
        await neo4j_service.connect()
        logger.info("Neo4j service connection verified.")
        logger.info("Attempting to create Neo4j constraints...")
        await neo4j_service.create_indexes() # Now only creates constraints
        logger.info("Neo4j constraint creation attempt finished.")

        # Connect to Milvus and ensure collection/index exists
        await milvus_service.connect()
        logger.info("Milvus service connected and collection/index checked.")

    except Exception as e:
        # Log connection or index creation errors
        logger.error(f"Failed during startup initialization: {e}", exc_info=True)
        # Depending on requirements, you might want to prevent startup if DB init fails
        # raise # Re-raise to potentially stop the app
    yield
    # Shutdown
    logger.info("Application shutdown...")
    await neo4j_service.close()
    logger.info("Neo4j service connection closed.")
    milvus_service.close()
    logger.info("Milvus service connection closed.")


# Create database tables moved to lifespan
# Base.metadata.create_all(bind=engine) # <--- REMOVE THIS LINE

# Configure Langfuse callback for request tracing
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_needs_to_be_changed")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "default_secret_key_needs_to_be_changed")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "default_public_key_needs_to_be_changed")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://34.66.130.204:3000")

langfuse_handler = CallbackHandler(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)

# Mount API routers
app = FastAPI(
    lifespan=lifespan,
)

# Redis limiter initialization removed

# Register rate limit exceeded exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for specified origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth.router) # Include the auth router
app.include_router(users.router) # Include the users router (now requires auth for some endpoints)
app.include_router(general.router)
app.include_router(ask.router)
