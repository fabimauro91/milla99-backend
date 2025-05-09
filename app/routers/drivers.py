from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.models.driver import Driver, DriverCreate, DriverFullCreate
from app.core.db import get_session
from app.models.user import UserRead
from app.services.driver_service import DriverService

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_driver(data: DriverFullCreate, session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.create_driver(
        user_data=data.user,
        driver_info_data=data.driver_info,
        vehicle_info_data=data.vehicle_info
    )


