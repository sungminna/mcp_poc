from fastapi import FastAPI
from dotenv import load_dotenv

from database import engine, Base # Import database engine and Base
from models import user as user_model # Import user model to create table

# Create database tables
user_model.Base.metadata.create_all(bind=engine)

load_dotenv()

from routers import general, ask, users, auth # Import the new auth router

app = FastAPI()

# Include the routers
app.include_router(auth.router) # Include the auth router
app.include_router(users.router) # Include the users router (now requires auth for some endpoints)
app.include_router(general.router)
app.include_router(ask.router)
