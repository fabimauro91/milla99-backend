import pytest
from sqlalchemy.orm import Session
from app.models.client_request import ClientRequest, StatusEnum
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.type_service import TypeService
from app.models.vehicle_type import VehicleType
from app.services.client_requests_service import (
    update_status_by_driver_service,
    update_status_by_client_service,
    update_status_to_paid_service
)
from fastapi import HTTPException


def create_test_data(session: Session) -> tuple[int, int, int]:
    """Crea todos los datos necesarios para las pruebas"""
    # Crear tipo de vehículo
    vehicle_type = VehicleType(
        name="Car",
        description="Carro particular"
    )
    session.add(vehicle_type)
    session.flush()

    # Crear tipo de servicio
    type_service = TypeService(
        name="Car Ride",
        description="Servicio de carro particular",
        vehicle_type_id=vehicle_type.id
    )
    session.add(type_service)
    session.flush()

    # Crear cliente
    client = User(
        full_name="Test Client",
        phone_number="3001111111",
        country_code="57"
    )
    session.add(client)
    session.flush()

    client_role = UserHasRole(
        id_user=client.id,
        id_rol="CLIENT",
        status=RoleStatus.APPROVED
    )
    session.add(client_role)

    # Crear conductor
    driver = User(
        full_name="Test Driver",
        phone_number="3002222222",
        country_code="57"
    )
    session.add(driver)
    session.flush()

    driver_role = UserHasRole(
        id_user=driver.id,
        id_rol="DRIVER",
        status=RoleStatus.APPROVED
    )
    session.add(driver_role)

    session.commit()
    return client.id, driver.id, type_service.id


def create_test_request(session: Session, client_id: int, type_service_id: int) -> ClientRequest:
    """Crea una solicitud de viaje de prueba"""
    request = ClientRequest(
        id_client=client_id,
        status=StatusEnum.CREATED,
        fare_offered=20000,
        pickup_description="Test Pickup",
        destination_description="Test Destination",
        type_service_id=type_service_id
    )
    session.add(request)
    session.commit()
    return request


def test_valid_driver_transitions(session: Session):
    """Prueba las transiciones válidas para el conductor"""
    client_id, driver_id, type_service_id = create_test_data(session)
    request = create_test_request(session, client_id, type_service_id)

    # Asignar conductor
    request.id_driver_assigned = driver_id
    request.status = StatusEnum.ACCEPTED
    session.commit()

    # Probar transiciones válidas
    valid_transitions = [
        (StatusEnum.ACCEPTED, StatusEnum.ON_THE_WAY),
        (StatusEnum.ON_THE_WAY, StatusEnum.ARRIVED),
        (StatusEnum.ARRIVED, StatusEnum.TRAVELLING),
        (StatusEnum.TRAVELLING, StatusEnum.FINISHED)
    ]

    for current, next_state in valid_transitions:
        request.status = current
        session.commit()

        result = update_status_by_driver_service(
            session, request.id, next_state.value, driver_id
        )
        assert result["success"] is True
        session.refresh(request)
        assert request.status == next_state


def test_invalid_driver_transitions(session: Session):
    """Prueba las transiciones inválidas para el conductor"""
    client_id, driver_id, type_service_id = create_test_data(session)
    request = create_test_request(session, client_id, type_service_id)
    request.id_driver_assigned = driver_id
    request.status = StatusEnum.ACCEPTED
    session.commit()

    # Probar transiciones inválidas
    invalid_transitions = [
        # Debe ir a ON_THE_WAY primero
        (StatusEnum.ACCEPTED, StatusEnum.ARRIVED),
        # Debe ir a ARRIVED primero
        (StatusEnum.ON_THE_WAY, StatusEnum.TRAVELLING),
        # Debe ir a TRAVELLING primero
        (StatusEnum.ARRIVED, StatusEnum.FINISHED),
        (StatusEnum.TRAVELLING, StatusEnum.ON_THE_WAY),  # No se puede retroceder
        (StatusEnum.FINISHED, StatusEnum.TRAVELLING)  # No se puede retroceder
    ]

    for current, next_state in invalid_transitions:
        request.status = current
        session.commit()

        with pytest.raises(HTTPException) as exc_info:
            update_status_by_driver_service(
                session, request.id, next_state.value, driver_id
            )
        assert exc_info.value.status_code == 400


def test_valid_client_transitions(session: Session):
    """Prueba las transiciones válidas para el cliente"""
    client_id, driver_id, type_service_id = create_test_data(session)
    request = create_test_request(session, client_id, type_service_id)

    # Probar cancelación desde CREATED
    result = update_status_by_client_service(
        session, request.id, StatusEnum.CANCELLED.value, client_id
    )
    assert result["success"] is True
    session.refresh(request)
    assert request.status == StatusEnum.CANCELLED

    # Crear nueva solicitud para probar cancelación desde ACCEPTED
    request = create_test_request(session, client_id, type_service_id)
    request.id_driver_assigned = driver_id
    request.status = StatusEnum.ACCEPTED
    session.commit()

    result = update_status_by_client_service(
        session, request.id, StatusEnum.CANCELLED.value, client_id
    )
    assert result["success"] is True
    session.refresh(request)
    assert request.status == StatusEnum.CANCELLED


def test_invalid_client_transitions(session: Session):
    """Prueba las transiciones inválidas para el cliente"""
    client_id, driver_id, type_service_id = create_test_data(session)
    request = create_test_request(session, client_id, type_service_id)
    request.id_driver_assigned = driver_id

    # Probar cancelación desde estados no permitidos
    invalid_states = [
        StatusEnum.ON_THE_WAY,
        StatusEnum.ARRIVED,
        StatusEnum.TRAVELLING,
        StatusEnum.FINISHED
    ]

    for state in invalid_states:
        request.status = state
        session.commit()

        with pytest.raises(HTTPException) as exc_info:
            update_status_by_client_service(
                session, request.id, StatusEnum.CANCELLED.value, client_id
            )
        assert exc_info.value.status_code == 400


def test_paid_status_transition(session: Session):
    """Prueba la transición al estado PAID"""
    client_id, driver_id, type_service_id = create_test_data(session)
    request = create_test_request(session, client_id, type_service_id)
    request.id_driver_assigned = driver_id

    # Intentar pagar desde estados inválidos
    invalid_states = [
        StatusEnum.CREATED,
        StatusEnum.ACCEPTED,
        StatusEnum.ON_THE_WAY,
        StatusEnum.ARRIVED,
        StatusEnum.TRAVELLING
    ]

    for state in invalid_states:
        request.status = state
        session.commit()

        with pytest.raises(HTTPException) as exc_info:
            update_status_to_paid_service(session, request.id, client_id)
        assert exc_info.value.status_code == 400

    # Probar pago desde FINISHED (válido)
    request.status = StatusEnum.FINISHED
    session.commit()

    result = update_status_to_paid_service(session, request.id, client_id)
    assert result["success"] is True
    session.refresh(request)
    assert request.status == StatusEnum.PAID


def test_unauthorized_status_changes(session: Session):
    """Prueba cambios de estado no autorizados"""
    client_id, driver_id, type_service_id = create_test_data(session)

    # Crear otros usuarios para probar autorizaciones
    other_client = User(
        full_name="Other Client",
        phone_number="3003333333",
        country_code="57"
    )
    session.add(other_client)
    session.flush()

    other_client_role = UserHasRole(
        id_user=other_client.id,
        id_rol="CLIENT",
        status=RoleStatus.APPROVED
    )
    session.add(other_client_role)

    other_driver = User(
        full_name="Other Driver",
        phone_number="3004444444",
        country_code="57"
    )
    session.add(other_driver)
    session.flush()

    other_driver_role = UserHasRole(
        id_user=other_driver.id,
        id_rol="DRIVER",
        status=RoleStatus.APPROVED
    )
    session.add(other_driver_role)
    session.commit()

    request = create_test_request(session, client_id, type_service_id)
    request.id_driver_assigned = driver_id
    request.status = StatusEnum.ACCEPTED
    session.commit()

    # Cliente intentando cambiar estado como conductor
    with pytest.raises(HTTPException) as exc_info:
        update_status_by_driver_service(
            session, request.id, StatusEnum.ON_THE_WAY.value, client_id
        )
    assert exc_info.value.status_code == 403

    # Conductor intentando cambiar estado como cliente
    with pytest.raises(HTTPException) as exc_info:
        update_status_by_client_service(
            session, request.id, StatusEnum.CANCELLED.value, driver_id
        )
    assert exc_info.value.status_code == 403

    # Cliente no dueño intentando cancelar
    with pytest.raises(HTTPException) as exc_info:
        update_status_by_client_service(
            session, request.id, StatusEnum.CANCELLED.value, other_client.id
        )
    assert exc_info.value.status_code == 403

    # Conductor no asignado intentando cambiar estado
    with pytest.raises(HTTPException) as exc_info:
        update_status_by_driver_service(
            session, request.id, StatusEnum.ON_THE_WAY.value, other_driver.id
        )
    assert exc_info.value.status_code == 403
