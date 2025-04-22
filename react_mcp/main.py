from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager # Import asynccontextmanager
import logging # Import logging

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

# --- Async function to create tables ---
async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables checked/created.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    try:
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

load_dotenv()

# Setup Langfuse
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_needs_to_be_changed")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "default_secret_key_needs_to_be_changed")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "default_public_key_needs_to_be_changed")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://34.66.130.204:3000")

langfuse_handler = CallbackHandler(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)

# Setup FastAPI
from routers import general, ask, users, auth # Import the new auth router

# Pass the lifespan context manager to the FastAPI app
app = FastAPI(lifespan=lifespan)

# Include the routers
app.include_router(auth.router) # Include the auth router
app.include_router(users.router) # Include the users router (now requires auth for some endpoints)
app.include_router(general.router)
app.include_router(ask.router)
