from fastapi import APIRouter, Depends, status, Request, HTTPException, Security, File, UploadFile, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Optional
from uuid import UUID

from app.core.dependencies.auth import user_is_owner
from app.models.user import User, UserCreate, UserUpdate, UserRead
from app.core.db import SessionDep
from app.services.user_service import UserService

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/users", tags=["users"])

# Create user endpoint (pública)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED, description="""
Crea un nuevo usuario en el sistema.

**Parámetros:**
- `full_name`: Nombre completo del usuario.
- `country_code`: Código de país.
- `phone_number`: Número de teléfono móvil.

**Respuesta:**
Devuelve el usuario creado con su información registrada.
""")
def create_user(
    session: SessionDep,
    user_data: UserCreate
):
    service = UserService(session)
    return service.create_user(user_data)

# List users endpoint (protegida)


@router.get("/", response_model=List[User], description="""
Obtiene la lista de todos los usuarios registrados en el sistema.

**Respuesta:**
Devuelve una lista de objetos de usuario con su información básica.
""")
def list_users(request: Request, session: SessionDep, credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    service = UserService(session)
    return service.get_users()

# Get current user endpoint (protegida y solo para el usuario autenticado)


@router.get("/me", response_model=UserRead, description="""
Obtiene la información del usuario autenticado (usando el token).

**Respuesta:**
Devuelve el objeto de usuario correspondiente al usuario autenticado.
""")
def get_current_user(request: Request, session: SessionDep, credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    user_id = request.state.user_id
    service = UserService(session)
    return service.get_user(user_id)

# Update user endpoint (protegida)
# @router.patch("/{user_id}", response_model=User)


def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    session: SessionDep,
    permission: None = Depends(user_is_owner()),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    service = UserService(session)
    return service.update_user(user_id, user_data)

# Delete user endpoint (protegida)
# @router.delete("/{user_id}", status_code=status.HTTP_200_OK)


def delete_user(user_id: int, request: Request, session: SessionDep):
    service = UserService(session)
    return service.delete_user(user_id)

# Verify user endpoint (protegida)
# @router.patch("/{user_id}/verify", response_model=User)


async def verify_user(user_id:  UUID, request: Request, session: SessionDep):
    service = UserService(session)
    return service.verify_user(user_id)

# Update selfie endpoint (protegida) – toma el user_id desde el token (request.state.user_id)


@router.patch("/selfie", status_code=status.HTTP_200_OK, description="""
Actualiza la selfie del usuario autenticado (se toma el user_id desde el token).
""")
def update_selfie(request: Request, session: SessionDep, selfie: UploadFile = File(...), credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    user_id = request.state.user_id
    service = UserService(session)
    return service.update_selfie(user_id, selfie)
