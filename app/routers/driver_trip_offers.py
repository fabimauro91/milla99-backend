from fastapi import APIRouter, status
from ..core.db import SessionDep
from app.services.driver_trip_offer_service import DriverTripOfferService,DriverTripOfferResponse
from app.models.driver_trip_offer import DriverTripOffer
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/driver-trip-offers",
    tags=["driver-trip-offers"]
)
# Modelos para las solicitudes y respuestas
class DriverTripOfferCreate(BaseModel):
    id_driver: int
    id_client_request: int
    fare_offered: float
    time: float
    distance: float

class FareUpdate(BaseModel):
    new_fare: float

class DriverInfo(BaseModel):
    id: int
    full_name: str | None = None
    phone_number: str | None = None
    country_code: str | None = None

# 1. Crear una nueva oferta de viaje
@router.post(
    "/",
    response_model=DriverTripOffer,
    status_code=status.HTTP_201_CREATED
)
async def create_offer(offer_data: DriverTripOfferCreate, session: SessionDep):
    service = DriverTripOfferService(session)
    return service.create_driver_trip_offer(offer_data.dict())

# 2. Listar todas las ofertas de un client_request del día de hoy, con datos del conductor
@router.get(
    "/client-request/{client_request_id}",
    response_model=List[DriverTripOfferResponse]
)
async def get_offers_by_client_request(client_request_id: int, session: SessionDep):
    service = DriverTripOfferService(session)
    return service.get_today_offers_by_client_request(client_request_id)

# 3. Modificar el valor de fare_offered (solo el conductor puede hacerlo)
@router.patch(
    "/{offer_id}/driver/{driver_id}/fare",
    response_model=DriverTripOffer
)
async def update_fare(
    offer_id: int,
    driver_id: int,
    fare_data: FareUpdate,
    session: SessionDep
):
    service = DriverTripOfferService(session)
    return service.update_fare_offered(offer_id, driver_id, fare_data.new_fare)