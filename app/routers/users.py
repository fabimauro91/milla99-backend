from fastapi import APIRouter, Depends, status, Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List

from app.core.dependencies.auth import user_is_owner
from app.models.user import User, UserCreate, UserUpdate, UserRead
from app.core.db import SessionDep
from app.services.user_service import UserService

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/users", tags=["users"])

# Create user endpoint (pública)
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, session: SessionDep):
    service = UserService(session)
    return service.create_user(user_data)

# List users endpoint (protegida)
@router.get("/", response_model=List[User])
def list_users(request: Request, session: SessionDep):
    service = UserService(session)
    return service.get_users()

# Get user by ID endpoint (protegida y solo para el usuario autenticado)
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, request: Request, session: SessionDep):
    service = UserService(session)
    return service.get_user(user_id)

# Update user endpoint (protegida)
#@router.patch("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: SessionDep,
    permission: None = Depends(user_is_owner()),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    service = UserService(session)
    return service.update_user(user_id, user_data)

# Delete user endpoint (protegida)
#@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, request: Request, session: SessionDep):
    service = UserService(session)
    return service.delete_user(user_id)

# Verify user endpoint (protegida)
#@router.patch("/{user_id}/verify", response_model=User)
async def verify_user(user_id: int, request: Request, session: SessionDep):
    service = UserService(session)
    return service.verify_user(user_id)
