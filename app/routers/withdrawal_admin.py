from fastapi import APIRouter, Depends, status, HTTPException, Request
from uuid import UUID
import logging

from app.core.dependencies.admin_auth import get_current_admin
from app.core.db import SessionDep
from app.services.withdrawal_service import WithdrawalService

router = APIRouter(
    prefix="/withdrawals",
    tags=["ADMIN: withdrawals"]
)


@router.patch("/{withdrawal_id}/update-status", status_code=status.HTTP_200_OK, description="""
Actualiza el estado de un retiro (withdrawal) por su ID. Este endpoint está separado y se agrupa en la sección de administración en Swagger.

**Parámetros:**
- `withdrawal_id`: UUID del retiro a actualizar.
- `new_status`: Nuevo estado (por ejemplo, "approved", "rejected", "pending").
- `request`: Objeto de request (para obtener el usuario autenticado).

**Respuesta:**
Devuelve el objeto de retiro actualizado.
""")
async def update_withdrawal_status(
    withdrawal_id: UUID,
    new_status: str,
    request: Request,
    session: SessionDep,
    current_admin=Depends(get_current_admin)
):
    service = WithdrawalService(session)
    try:
        return service.update_status(withdrawal_id, new_status, request.state.admin_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.exception("Unexpected error updating withdrawal status")
        raise HTTPException(status_code=500, detail="Internal server error")
