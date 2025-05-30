from fastapi import APIRouter, Depends, status, Request, Security
from sqlalchemy.orm import Session
from app.models.driver_trip_offer import DriverTripOfferCreate, DriverTripOffer, DriverTripOfferResponse
from app.core.db import get_session
from app.services.driver_trip_offer_service import DriverTripOfferService
from uuid import UUID
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/driver-trip-offers", tags=["driver-trip-offers"])

bearer_scheme = HTTPBearer()


@router.post("/", response_model=DriverTripOffer, status_code=status.HTTP_201_CREATED, description="""
Crea una nueva oferta de viaje por parte de un conductor para una solicitud de cliente.

**Parámetros:**
- `id_client_request`: ID de la solicitud de viaje del cliente.
- `fare_offer`: Tarifa ofrecida por el conductor.
- `time`: Tiempo estimado del viaje.
- `distance`: Distancia estimada del viaje.

**Respuesta:**
Devuelve la oferta de viaje creada con toda su información.
""")
def create_driver_trip_offer(
    request: Request,
    data: DriverTripOfferCreate,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    user_id = request.state.user_id
    # Creamos un nuevo objeto con el id_driver del token
    data_dict = data.dict()
    data_dict["id_driver"] = user_id
    service = DriverTripOfferService(session)
    return service.create_offer(data_dict)


@router.get("/by-client-request/{id_client_request}", response_model=list[DriverTripOfferResponse], description="""
Obtiene todas las ofertas de viaje realizadas por conductores para una solicitud de cliente específica.

**Parámetros:**
- `id_client_request`: ID de la solicitud de viaje del cliente.

**Respuesta:**
Devuelve una lista de ofertas de viaje, incluyendo información del conductor, usuario y vehículo.
""")
def get_offers_by_client_request(
    id_client_request: UUID,
    session: Session = Depends(get_session)
):
    service = DriverTripOfferService(session)
    return service.get_offers_by_client_request(id_client_request)
