from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.models.driver import Driver, DriverCreate, DriverUpdate
from app.core.db import get_session
from app.services.driver_service import DriverService

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("/", response_model=Driver, status_code=status.HTTP_201_CREATED)
def create_driver(driver_data: DriverCreate, session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.create_driver(driver_data)


@router.get("/", response_model=List[Driver])
def list_drivers(session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.get_all_drivers()


@router.get("/{driver_id}", response_model=Driver)
def get_driver(driver_id: int, session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.get_driver_by_id(driver_id)


@router.patch("/{driver_id}", response_model=Driver)
def update_driver(driver_id: int, driver_data: DriverUpdate, session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.update_driver(driver_id, driver_data)


@router.delete("/{driver_id}", status_code=status.HTTP_200_OK)
def delete_driver(driver_id: int, session: Session = Depends(get_session)):
    service = DriverService(session)
    return service.soft_delete_driver(driver_id)

