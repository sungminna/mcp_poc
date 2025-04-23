from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio # Import asyncio
import logging # Import logging

from models.user import UserCreate, UserResponse, User
from crud import user as crud_user
from database import get_db
from core.security import get_current_active_user
from services.neo4j_service import neo4j_service # Import Neo4j service
from main import limiter, DEFAULT_REGISTER_LIMIT  # Import the limiter and rate limit

router = APIRouter()
logger = logging.getLogger(__name__) # Setup logger

# User creation endpoint (public)
@router.post("/api/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["users"])
@limiter.limit(DEFAULT_REGISTER_LIMIT)  # Use configurable registration rate limit
async def create_user_endpoint(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user_by_username = await crud_user.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_by_email = await crud_user.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user in the primary database
    created_user = await crud_user.create_user(db=db, user=user)

    # After successful creation in primary DB, add to Neo4j
    try:
        # Run the async Neo4j call in the background
        asyncio.create_task(
            neo4j_service.add_user(username=created_user.username, user_info=user.dict())
        )
        logger.info(f"Neo4j add_user task created for user '{created_user.username}'")
    except Exception as e:
        # Log the error but don't fail the user creation process
        logger.error(f"Failed to initiate Neo4j user creation for '{created_user.username}': {e}")

    return created_user # Return the user object from the primary DB

# Endpoint to get current authenticated user's details
@router.get("/api/users/me", response_model=UserResponse, tags=["users"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Endpoint to get a specific user by ID (requires authentication)
@router.get("/api/users/{user_id}", response_model=UserResponse, tags=["users"])
async def read_user_endpoint(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # You might want to add permission checks here, e.g., if only admin or the user themselves can access
    db_user = await crud_user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Endpoint to get a list of users (requires authentication)
# Consider adding pagination and potentially admin-only access
@router.get("/api/users/", response_model=List[UserResponse], tags=["users"])
async def read_users_endpoint(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # Add permission checks if needed (e.g., only admins can list all users)
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users

# TODO: Add endpoints for updating and deleting users if needed (with auth)

# @router.put("/users/{user_id}", response_model=User, tags=["users"])
# async def update_user(...): ...

# @router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
# async def delete_user(...): ... 