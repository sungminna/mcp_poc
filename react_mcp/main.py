"""Main application module: configures FastAPI app with lifecycle events, database schema initialization, graph and vector services setup, rate limiting, CORS, and API routers."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from core.depends import limiter

from database import engine, Base, get_db
import models.chat
from models import user as user_model
from services.neo4j_service import neo4j_service
from services.milvus_service import milvus_service
from core.config import CORS_ALLOW_ORIGINS
from routers import auth, users, general, ask
from utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

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

# Database tables are created in the lifespan context

# Mount API routers
app = FastAPI(lifespan=lifespan)

# Register rate limit exceeded exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for specified origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include versioned API routers
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth, prefix="/auth", tags=["auth"])
api_router.include_router(users, prefix="/users", tags=["users"])
api_router.include_router(ask, prefix="/chat", tags=["chat"])
api_router.include_router(general, tags=["general"])
app.include_router(api_router)
