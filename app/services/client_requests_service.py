from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from app.models.client_requests import ClientRequest, ClientRequestCreate


def create_client_request(db: Session, data: ClientRequestCreate):
    pickup_point = from_shape(
        Point(data.pickup_lng, data.pickup_lat), srid=4326)
    destination_point = from_shape(
        Point(data.destination_lng, data.destination_lat), srid=4326)
    db_obj = ClientRequest(
        id_client=data.id_client,
        fare_offered=data.fare_offered,
        fare_assigned=data.fare_assigned,
        pickup_description=data.pickup_description,
        destination_description=data.destination_description,
        client_rating=data.client_rating,
        driver_rating=data.driver_rating,
        pickup_position=pickup_point,
        destination_position=destination_point,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
