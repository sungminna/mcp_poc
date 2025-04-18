from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager # Import asynccontextmanager
import logging # Import logging

from database import engine, Base # Import database engine and Base
from models import user as user_model # Import user model to create table
from services.neo4j_service import neo4j_service # Import the Neo4j service instance

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup...")
    try:
        neo4j_service.connect() # Connect to Neo4j
        logger.info("Neo4j service connected.")
        # Attempt to create indexes after connection
        logger.info("Attempting to create Neo4j indexes...")
        await neo4j_service.create_indexes()
        logger.info("Neo4j index creation attempt finished.")
    except Exception as e:
        # Log connection or index creation errors
        logger.error(f"Failed during Neo4j service initialization (connect/create_indexes): {e}", exc_info=True)
        # Depending on requirements, you might want to prevent startup if DB init fails
        # raise HTTPException(status_code=500, detail="Database initialization failed")
    yield
    # Shutdown
    logger.info("Application shutdown...")
    neo4j_service.close()
    logger.info("Neo4j service connection closed.")


# Create database tables (assuming this is for a relational DB like Postgres/SQLite)
user_model.Base.metadata.create_all(bind=engine)

load_dotenv()

from routers import general, ask, users, auth # Import the new auth router

# Pass the lifespan context manager to the FastAPI app
app = FastAPI(lifespan=lifespan)

# Include the routers
app.include_router(auth.router) # Include the auth router
app.include_router(users.router) # Include the users router (now requires auth for some endpoints)
app.include_router(general.router)
app.include_router(ask.router)
