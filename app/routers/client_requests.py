from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.core.db import get_session
from app.models.client_requests import ClientRequestCreate, ClientRequest
from app.services.client_requests_service import create_client_request

router = APIRouter(prefix="/client-requests", tags=["Client Requests"])


@router.post("/", response_model=ClientRequest, status_code=status.HTTP_201_CREATED)
def create_request(request: ClientRequestCreate, session: Session = Depends(get_session)):
    try:
        db_obj = create_client_request(session, request)
        return db_obj
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la solicitud de viaje: {str(e)}")
