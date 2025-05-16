from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.models.driver_trip_offer import DriverTripOfferCreate, DriverTripOffer, DriverTripOfferResponse
from app.core.db import get_session
from app.services.driver_trip_offer_service import DriverTripOfferService

router = APIRouter(prefix="/driver-trip-offers", tags=["driver-trip-offers"])

@router.post("/", response_model=DriverTripOffer, status_code=status.HTTP_201_CREATED)
def create_driver_trip_offer(
    data: DriverTripOfferCreate,
    session: Session = Depends(get_session)
):
    service = DriverTripOfferService(session)
    return service.create_offer(data)

@router.get("/by-client-request/{id_client_request}", response_model=list[DriverTripOfferResponse])
def get_offers_by_client_request(
    id_client_request: int,
    session: Session = Depends(get_session)
):
    service = DriverTripOfferService(session)
    return service.get_offers_by_client_request(id_client_request) 