from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.client_requests import ClientRequestCreate, ClientRequest
from app.services.client_requests_service import create_client_request
from app.dependencies import get_db

router = APIRouter(prefix="/client-requests", tags=["Client Requests"])


@router.post("/", response_model=ClientRequest, status_code=status.HTTP_201_CREATED)
def create_request(request: ClientRequestCreate, db: Session = Depends(get_db)):
    try:
        db_obj = create_client_request(db, request)
        return db_obj
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la solicitud de viaje: {str(e)}")
