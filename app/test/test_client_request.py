from fastapi.testclient import TestClient
from app.main import app
from app.test.test_drivers import create_and_approve_driver
from app.models.client_request import StatusEnum

client = TestClient(app)


def test_create_client_request():
    # Datos del cliente
    phone_number = "3004444456"
    country_code = "+57"

    # Enviar código de verificación
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    # Verificar el código y obtener el token
    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Datos de la solicitud
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
    response = client.post(
        "/client-request/", json=request_data, headers=headers)
    assert response.status_code == 201
    assert "id" in response.json()


def test_assign_driver_to_client_request():
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


def test_driver_changes_status_to_ontheway():
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

    # Consultar el detalle de la solicitud y verificar el estado
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=driver_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == str(StatusEnum.ON_THE_WAY)


def test_driver_changes_status_to_arrived():
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

    # Consultar el detalle de la solicitud y verificar el estado
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=driver_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == str(StatusEnum.ARRIVED)


def test_driver_changes_status_to_travelling():
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

    # Cambiar el estado a TRAVELLING
    status_data_travelling = {
        "id_client_request": client_request_id,
        "status": "TRAVELLING"
    }
    status_resp_travelling = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_travelling, headers=driver_headers)
    assert status_resp_travelling.status_code == 200
    assert status_resp_travelling.json()["success"] is True

    # Consultar el detalle de la solicitud y verificar el estado
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=driver_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == str(StatusEnum.TRAVELLING)


def test_driver_changes_status_to_finished():
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

    # Cambiar el estado a TRAVELLING
    status_data_travelling = {
        "id_client_request": client_request_id,
        "status": "TRAVELLING"
    }
    status_resp_travelling = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_travelling, headers=driver_headers)
    assert status_resp_travelling.status_code == 200
    assert status_resp_travelling.json()["success"] is True

    # Cambiar el estado a FINISHED
    status_data_finished = {
        "id_client_request": client_request_id,
        "status": "FINISHED"
    }
    status_resp_finished = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_finished, headers=driver_headers)
    assert status_resp_finished.status_code == 200
    assert status_resp_finished.json()["success"] is True

    # Consultar el detalle de la solicitud y verificar el estado
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=driver_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == str(StatusEnum.FINISHED)


def test_driver_changes_status_to_paid():
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

    # Cambiar el estado a TRAVELLING
    status_data_travelling = {
        "id_client_request": client_request_id,
        "status": "TRAVELLING"
    }
    status_resp_travelling = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_travelling, headers=driver_headers)
    assert status_resp_travelling.status_code == 200
    assert status_resp_travelling.json()["success"] is True

    # Cambiar el estado a FINISHED
    status_data_finished = {
        "id_client_request": client_request_id,
        "status": "FINISHED"
    }
    status_resp_finished = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_finished, headers=driver_headers)
    assert status_resp_finished.status_code == 200
    assert status_resp_finished.json()["success"] is True

    # Cambiar el estado a PAID
    status_data_paid = {
        "id_client_request": client_request_id,
        "status": "PAID"
    }
    status_resp_paid = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_paid, headers=driver_headers)
    assert status_resp_paid.status_code == 200
    assert status_resp_paid.json()["success"] is True

    # Consultar el detalle de la solicitud y verificar el estado
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=driver_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == str(StatusEnum.PAID)


def test_driver_cannot_skip_states_to_finished():
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

    # Intentar saltar de ACCEPTED a FINISHED
    status_data_finished = {
        "id_client_request": client_request_id,
        "status": "FINISHED"
    }
    status_resp_finished = client.patch(
        "/client-request/updateStatusByDriver", json=status_data_finished, headers=driver_headers)
    assert status_resp_finished.status_code == 400
    assert "Transición de estado no permitida" in status_resp_finished.json()[
        "detail"]


def test_client_cancel_request():
    """
    Test básico para verificar que el endpoint de cancelación del cliente funciona.
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

    # Intentar cancelar la solicitud
    cancel_data = {
        "id_client_request": client_request_id
    }
    cancel_resp = client.patch(
        "/client-request/clientCanceled", json=cancel_data, headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["success"] is True
    assert "Solicitud cancelada" in cancel_resp.json()["message"]

    # Verificar que el estado de la solicitud cambió a CANCELLED
    detail_resp = client.get(
        f"/client-request/{client_request_id}", headers=headers)
    assert detail_resp.status_code == 200

    # Imprimir información para debug
    print("\n=== DEBUG INFO ===")
    print(f"Status from API: {detail_resp.json()['status']}")
    print(f"Type of status: {type(detail_resp.json()['status'])}")
    print(f"StatusEnum.CANCELLED value: {StatusEnum.CANCELLED}")
    print(f"StatusEnum.CANCELLED type: {type(StatusEnum.CANCELLED)}")
    print("=================\n")

    # Comparar con el valor del enum
    assert detail_resp.json()["status"] == str(StatusEnum.CANCELLED)
