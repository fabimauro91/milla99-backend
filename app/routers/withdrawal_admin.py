from fastapi import APIRouter, Depends, status, HTTPException, Request
from uuid import UUID
import logging
from pydantic import BaseModel

from app.core.dependencies.admin_auth import get_current_admin
from app.core.db import SessionDep
from app.services.withdrawal_service import WithdrawalService

router = APIRouter(
    prefix="/withdrawals",
    tags=["ADMIN: withdrawals"]
)


class UpdateWithdrawalStatusRequest(BaseModel):
    new_status: str


@router.patch("/{withdrawal_id}/update-status", status_code=status.HTTP_200_OK, description="""
Actualiza el estado de un retiro (withdrawal) por su ID. Este endpoint está separado y se agrupa en la sección de administración en Swagger.

**Parámetros:**
- `withdrawal_id`: UUID del retiro a actualizar.
- `new_status`: Nuevo estado (por ejemplo, "approved", "rejected").

**Respuesta:**
Devuelve el objeto de retiro actualizado.
""")
async def update_withdrawal_status(
    withdrawal_id: UUID,
    data: UpdateWithdrawalStatusRequest,
    request: Request,
    session: SessionDep,
    current_admin=Depends(get_current_admin)
):
    service = WithdrawalService(session)
    try:
        if data.new_status == "approved":
            return service.approve_withdrawal(withdrawal_id)
        elif data.new_status == "rejected":
            return service.reject_withdrawal(withdrawal_id)
        else:
            raise HTTPException(
                status_code=400, detail="Invalid or unsupported status")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.exception("Unexpected error updating withdrawal status")
        raise HTTPException(status_code=500, detail="Internal server error")
