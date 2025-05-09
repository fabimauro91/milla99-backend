from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session
from app.core.db import get_session
from app.models.driver_info import DriverInfo, DriverInfoBase
from typing import Optional

router = APIRouter(prefix="/driver-info/{user_id}", tags=["driver-info"])


@router.post("/", response_model=DriverInfo, status_code=status.HTTP_201_CREATED)
def create_driver_info(
    driver_info: DriverInfoBase,
    user_id: int = None,
    session: Session = Depends(get_session)
):
    # Validar que user_id venga en el body o en el objeto
    if not user_id and not getattr(driver_info, "user_id", None):
        raise HTTPException(status_code=400, detail="user_id es requerido")
    # Prioridad: user_id explícito
    user_id = user_id or getattr(driver_info, "user_id")
    # Crear el objeto
    new_driver_info = DriverInfo(**driver_info.dict(), user_id=user_id)
    session.add(new_driver_info)
    session.commit()
    session.refresh(new_driver_info)
    return new_driver_info
