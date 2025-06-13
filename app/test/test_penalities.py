from fastapi.testclient import TestClient
from app.main import app
from app.test.test_drivers import create_and_approve_driver
from app.models.client_request import StatusEnum
from app.models.penality_user import statusEnum, PenalityUser
from app.models.project_settings import ProjectSettings
from decimal import Decimal
from uuid import UUID
import pytest
from sqlmodel import Session

client = TestClient(app)


def test_driver_cancellation_penalty_on_the_way(session: Session):
    """
    Test case for driver cancellation penalty when driver cancels in ON_THE_WAY state.
    Should apply fine_one (1000 pesos) penalty.
    """
    # Datos del cliente
    phone_number = "3004444456"
    country_code = "+57"

    # Autenticar cliente
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Crear solicitud de cliente
    request_data = {
        "fare_offered": 20000,
        "pickup_description": "Suba Bogotá",
        "destination_description": "Santa Rosita Engativa",
        "pickup_lat": 4.718136,
        "pickup_lng": -74.073170,
        "destination_lat": 4.702468,
        "destination_lng": -74.109776,
        "type_service_id": 1,  # Car
        "payment_method_id": 1  # Cash
    }
    create_resp = client.post(
        "/client-request/", json=request_data, headers=headers)
    assert create_resp.status_code == 201
    client_request_id = create_resp.json()["id"]

    # Crear y aprobar conductor
    driver_phone = "3010000005"
    driver_country_code = "+57"
    driver_token, driver_id = create_and_approve_driver(
        client, driver_phone, driver_country_code)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    # Asignar el conductor a la solicitud
    assign_data = {
        "id_client_request": client_request_id,
        "id_driver": driver_id,
        "fare_assigned": 25000
    }
    assign_resp = client.patch(
        "/client-request/updateDriverAssigned", json=assign_data, headers=headers)
    assert assign_resp.status_code == 200
    assert assign_resp.json()["success"] is True

    # Cambiar el estado a ON_THE_WAY
    status_data = {
        "id_client_request": client_request_id,
        "status": "ON_THE_WAY"
    }
    status_resp = client.patch(
        "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["success"] is True

    # Driver cancels the request
    cancel_data = {
        "id_client_request": client_request_id,
        "reason": "Test cancellation in ON_THE_WAY state"
    }
    cancel_resp = client.patch(
        "/client-request/driver-canceled", json=cancel_data, headers=driver_headers)
    assert cancel_resp.status_code == 200

    # Verify the penalty was created with correct amount (1000 pesos)
    penalty = session.query(PenalityUser).filter(
        PenalityUser.id_client_request == client_request_id,
        PenalityUser.id_driver_assigned == driver_id
    ).first()

    assert penalty is not None
    assert penalty.amount == Decimal('1000')
    assert penalty.status == statusEnum.PENDING
    assert penalty.id_user == UUID(str(create_resp.json()["id_client"]))


def test_driver_cancellation_penalty_arrived(session: Session):
    """
    Test case for driver cancellation penalty when driver cancels in ARRIVED state.
    Should apply fine_two (2000 pesos) penalty.
    """
    # Datos del cliente
    phone_number = "3004444457"
    country_code = "+57"

    # Autenticar cliente
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Crear solicitud de cliente
    request_data = {
        "fare_offered": 20000,
        "pickup_description": "Suba Bogotá",
        "destination_description": "Santa Rosita Engativa",
        "pickup_lat": 4.718136,
        "pickup_lng": -74.073170,
        "destination_lat": 4.702468,
        "destination_lng": -74.109776,
        "type_service_id": 1,  # Car
        "payment_method_id": 1  # Cash
    }
    create_resp = client.post(
        "/client-request/", json=request_data, headers=headers)
    assert create_resp.status_code == 201
    client_request_id = create_resp.json()["id"]

    # Crear y aprobar conductor
    driver_phone = "3010000006"
    driver_country_code = "+57"
    driver_token, driver_id = create_and_approve_driver(
        client, driver_phone, driver_country_code)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    # Asignar el conductor a la solicitud
    assign_data = {
        "id_client_request": client_request_id,
        "id_driver": driver_id,
        "fare_assigned": 25000
    }
    assign_resp = client.patch(
        "/client-request/updateDriverAssigned", json=assign_data, headers=headers)
    assert assign_resp.status_code == 200
    assert assign_resp.json()["success"] is True

    # Cambiar el estado a ON_THE_WAY
    status_data_ontheway = {
        "id_client_request": client_request_id,
        "status": "ON_THE_WAY"
    }
    status_resp_ontheway = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_ontheway, headers=driver_headers)
    assert status_resp_ontheway.status_code == 200
    assert status_resp_ontheway.json()["success"] is True

    # Cambiar el estado a ARRIVED
    status_data_arrived = {
        "id_client_request": client_request_id,
        "status": "ARRIVED"
    }
    status_resp_arrived = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_arrived, headers=driver_headers)
    assert status_resp_arrived.status_code == 200
    assert status_resp_arrived.json()["success"] is True

    # Driver cancels the request
    cancel_data = {
        "id_client_request": client_request_id,
        "reason": "Test cancellation in ARRIVED state"
    }
    cancel_resp = client.patch(
        "/client-request/driver-canceled", json=cancel_data, headers=driver_headers)
    assert cancel_resp.status_code == 200

    # Verify the penalty was created with correct amount (2000 pesos)
    penalty = session.query(PenalityUser).filter(
        PenalityUser.id_client_request == client_request_id,
        PenalityUser.id_driver_assigned == driver_id
    ).first()

    assert penalty is not None
    assert penalty.amount == Decimal('2000')
    assert penalty.status == statusEnum.PENDING
    assert penalty.id_user == UUID(str(create_resp.json()["id_client"]))
