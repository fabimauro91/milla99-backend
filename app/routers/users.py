from fastapi import APIRouter, Depends, status
from typing import List

from app.models.user import User, UserCreate, UserUpdate
from app.core.db import SessionDep
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

# Create user endpoint


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, session: SessionDep):
    service = UserService(session)
    return service.create_user(user_data)

# List users endpoint


@router.get("/", response_model=List[User])
def list_users(session: SessionDep):
    service = UserService(session)
    return service.get_users()

# Get user by ID endpoint


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, session: SessionDep):
    service = UserService(session)
    return service.get_user(user_id)

# Update user endpoint


@router.patch("/{user_id}", response_model=User)
def update_user(user_id: int, user_data: UserUpdate, session: SessionDep):
    service = UserService(session)
    return service.update_user(user_id, user_data)

# Delete user endpoint


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, session: SessionDep):
    service = UserService(session)
    return service.delete_user(user_id)

# Verify user endpoint


@router.patch("/{user_id}/verify", response_model=User, tags=["users"])
async def verify_user(user_id: int, session: SessionDep):
    service = UserService(session)
    return service.verify_user(user_id)
