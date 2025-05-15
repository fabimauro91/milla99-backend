from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.driver_position import DriverPositionCreate, DriverPositionRead
from app.core.db import get_session
from app.services.driver_position_service import DriverPositionService

router = APIRouter(prefix="/drivers-position", tags=["drivers-position"])

@router.post("/", response_model=DriverPositionRead, status_code=status.HTTP_201_CREATED)
def create_driver_position(
    data: DriverPositionCreate,
    session: Session = Depends(get_session)
):
    service = DriverPositionService(session)
    obj = service.create_driver_position(data)
    return DriverPositionRead.from_orm_with_point(obj) 