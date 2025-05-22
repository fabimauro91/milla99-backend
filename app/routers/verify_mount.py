from fastapi import APIRouter, Depends, Request
from app.core.db import SessionDep
from app.services.verify_mount_service import VerifyMountService

router = APIRouter(prefix="/verify-mount", tags=["verify_mount"])


@router.get("/me", description="Consulta el mount de verify_mount para el usuario autenticado.")
def get_my_mount(request: Request, session: SessionDep):
    user_id = request.state.user_id
    service = VerifyMountService(session)
    return service.get_mount(user_id)


# @router.put("/{user_id}", description="Actualiza el mount de verify_mount para un usuario.")
# def update_mount(user_id: int, new_mount: int, session: SessionDep):
#     service = VerifyMountService(session)
#     return service.update_mount(user_id, new_mount)
