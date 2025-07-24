from fastapi.testclient import TestClient
from app.main import app
from app.test.test_drivers import create_and_approve_driver
from app.models.client_request import StatusEnum
from app.core.db import engine
from sqlmodel import Session, select
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
import traceback
from datetime import datetime
from uuid import UUID

client = TestClient(app)


def create_and_approve_client(client, phone_number, country_code):
    """
    Función helper para crear y aprobar un cliente para tests
    """
    print(f"[DEBUG] 🔍 Verificando usuario: {phone_number}")

    # Verificar si el usuario ya existe
    with Session(engine) as session:
        existing_user = session.exec(select(User).where(
            User.phone_number == phone_number)).first()

        if existing_user:
            print(f"[DEBUG] ✅ Usuario encontrado: {existing_user.id}")
            # Usuario ya existe, verificar si tiene rol CLIENT
            client_role = session.exec(select(UserHasRole).where(
                UserHasRole.id_user == existing_user.id,
                UserHasRole.id_rol == "CLIENT")).first()

            print(
                f"[DEBUG] 🔍 Rol CLIENT encontrado: {client_role is not None}")
            if client_role:
                print(f"[DEBUG] 📋 Estado del rol: {client_role.status}")

            if client_role is None:
                print(f"[DEBUG] ➕ Asignando rol CLIENT a usuario existente")
                # Usuario existe pero no tiene rol CLIENT, asignarlo
                client_role = UserHasRole(
                    id_user=existing_user.id,
                    id_rol="CLIENT",
                    status=RoleStatus.APPROVED
                )
                session.add(client_role)
                try:
                    session.commit()
                    print(f"[DEBUG] ✅ Rol CLIENT asignado exitosamente")
                except Exception as e:
                    print(f"[DEBUG] ❌ Error al asignar rol: {e}")
                    print(f"[DEBUG] 📋 Traceback:")
                    import traceback
                    traceback.print_exc()
                    session.rollback()
                    raise
            elif client_role.status != RoleStatus.APPROVED:
                print(f"[DEBUG] 🔄 Aprobando rol CLIENT existente")
                # Usuario tiene rol pero no está aprobado, aprobarlo
                client_role.status = RoleStatus.APPROVED
                session.add(client_role)
                try:
                    session.commit()
                    print(f"[DEBUG] ✅ Rol CLIENT aprobado exitosamente")
                except Exception as e:
                    print(f"[DEBUG] ❌ Error al aprobar rol: {e}")
                    print(f"[DEBUG] 📋 Traceback:")
                    import traceback
                    traceback.print_exc()
                    session.rollback()
                    raise
            else:
                print(f"[DEBUG] ✅ Usuario ya tiene rol CLIENT aprobado")

            client_id = existing_user.id
        else:
            print(f"[DEBUG] ➕ Creando usuario nuevo: {phone_number}")
            # Crear usuario nuevo
            user_data = {
                "full_name": f"Client Test User",
                "country_code": country_code,
                "phone_number": phone_number
            }
            response = client.post("/users/", json=user_data)
            print(f"[DEBUG] 📡 Respuesta crear usuario: {response.status_code}")
            if response.status_code != 201:
                print(f"[DEBUG] ❌ Error en respuesta: {response.text}")
            assert response.status_code == 201, f"Error creando cliente ({phone_number}): {response.text}"
            user_data = response.json()
            client_id = UUID(user_data["id"])
            print(f"[DEBUG] ✅ Usuario creado con ID: {client_id}")

            # El endpoint /users/ ya crea automáticamente el rol CLIENT
            # Solo necesitamos verificar que esté aprobado
            client_role = session.exec(select(UserHasRole).where(
                UserHasRole.id_user == client_id,
                UserHasRole.id_rol == "CLIENT")).first()

            if client_role and client_role.status != RoleStatus.APPROVED:
                print(f"[DEBUG] 🔄 Aprobando rol CLIENT del usuario nuevo")
                client_role.status = RoleStatus.APPROVED
                session.add(client_role)
                try:
                    session.commit()
                    print(f"[DEBUG] ✅ Rol CLIENT aprobado para usuario nuevo")
                except Exception as e:
                    print(f"[DEBUG] ❌ Error al aprobar rol: {e}")
                    print(f"[DEBUG] 📋 Traceback:")
                    import traceback
                    traceback.print_exc()
                    session.rollback()
                    raise
            else:
                print(f"[DEBUG] ✅ Usuario nuevo ya tiene rol CLIENT aprobado")

    print(f"[DEBUG] 🔐 Autenticando usuario: {phone_number}")
    # Autenticar
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    print(f"[DEBUG] 📡 Respuesta enviar código: {send_resp.status_code}")
    if send_resp.status_code != 201:
        print(f"[DEBUG] ❌ Error enviando código: {send_resp.text}")
    assert send_resp.status_code == 201, f"Falló al enviar código a {phone_number}: {send_resp.text}"

    code = send_resp.json()["message"].split()[-1]
    print(f"[DEBUG] 📱 Código obtenido: {code}")
    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code", json={"code": code})
    print(f"[DEBUG] 📡 Respuesta verificar código: {verify_resp.status_code}")
    if verify_resp.status_code != 200:
        print(f"[DEBUG] ❌ Error verificando código: {verify_resp.text}")
    assert verify_resp.status_code == 200, f"Falló al verificar código para {phone_number}: {verify_resp.text}"

    client_token = verify_resp.json()["access_token"]
    print(f"[DEBUG] ✅ Usuario autenticado exitosamente")
    return client_token, client_id


def test_trip_with_multiple_stops():
    # 1. Crear y autenticar cliente
    phone_number = "3005555555"
    country_code = "+57"
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

    # Asegurar que el usuario tiene el rol CLIENT aprobado
    with Session(engine) as session:
        user = session.exec(select(User).where(
            User.phone_number == phone_number)).first()
        if user:
            client_role = session.exec(select(UserHasRole).where(
                UserHasRole.id_user == user.id, UserHasRole.id_rol == "CLIENT")).first()
            if client_role is None:
                client_role = UserHasRole(
                    id_user=user.id,
                    id_rol="CLIENT",
                    status=RoleStatus.APPROVED
                )
                session.add(client_role)
                session.commit()
            elif client_role.status != RoleStatus.APPROVED:
                client_role.status = RoleStatus.APPROVED
                session.add(client_role)
                session.commit()

    try:
        # 2. Crear solicitud de viaje con 2 paradas intermedias
        request_data = {
            "fare_offered": 30000,
            "pickup_description": "Origen (pickup)",
            "destination_description": "Destino (casa)",
            "pickup_lat": 4.700000,
            "pickup_lng": -74.100000,
            "destination_lat": 4.710000,
            "destination_lng": -74.110000,
            "type_service_id": 1,
            "payment_method_id": 1,
            "intermediate_stops": [
                {"latitude": 4.705000, "longitude": -74.105000,
                    "description": "Parada 1 (banco)"},
                {"latitude": 4.707000, "longitude": -74.108000,
                    "description": "Parada 2 (paquetería)"}
            ]
        }
        create_resp = client.post(
            "/client-request/", json=request_data, headers=headers)
        print("[DEBUG] Crear solicitud:",
              create_resp.status_code, create_resp.text)
        assert create_resp.status_code == 201, f"Error al crear solicitud: {create_resp.text}"
        client_request_id = create_resp.json()["id"]

        # 3. Crear y aprobar conductor
        driver_phone = "3015555555"
        driver_country_code = "+57"
        driver_token, driver_id = create_and_approve_driver(
            client, driver_phone, driver_country_code)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        # 4. Asignar conductor
        assign_data = {
            "id_client_request": client_request_id,
            "id_driver": str(driver_id),  # Convertir UUID a string para JSON
            "fare_assigned": 35000
        }
        assign_resp = client.patch(
            "/client-request/updateDriverAssigned", json=assign_data, headers=headers)
        print("[DEBUG] Asignar conductor:",
              assign_resp.status_code, assign_resp.text)
        assert assign_resp.status_code == 200, f"Error al asignar conductor: {assign_resp.text}"
        assert assign_resp.json()["success"] is True

        # 5. Cambiar estado a ON_THE_WAY
        status_data = {"id_client_request": client_request_id,
                       "status": "ON_THE_WAY"}
        status_resp = client.patch(
            "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
        print("[DEBUG] Estado ON_THE_WAY:",
              status_resp.status_code, status_resp.text)
        assert status_resp.status_code == 200, f"Error ON_THE_WAY: {status_resp.text}"
        assert status_resp.json()["success"] is True

        # 6. Cambiar estado a ARRIVED
        status_data = {
            "id_client_request": client_request_id, "status": "ARRIVED"}
        status_resp = client.patch(
            "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
        print("[DEBUG] Estado ARRIVED:",
              status_resp.status_code, status_resp.text)
        assert status_resp.status_code == 200, f"Error ARRIVED: {status_resp.text}"
        assert status_resp.json()["success"] is True

        # 7. Cambiar estado a TRAVELLING
        status_data = {"id_client_request": client_request_id,
                       "status": "TRAVELLING"}
        status_resp = client.patch(
            "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
        print("[DEBUG] Estado TRAVELLING:",
              status_resp.status_code, status_resp.text)
        assert status_resp.status_code == 200, f"Error TRAVELLING: {status_resp.text}"
        assert status_resp.json()["success"] is True

        # 8. Consultar detalle del viaje antes de pedir paradas
        detail_resp = client.get(
            f"/client-request/{client_request_id}", headers=driver_headers)
        print("[DEBUG] Detalle del viaje:",
              detail_resp.status_code, detail_resp.text)
        assert detail_resp.status_code == 200, f"Detalle no encontrado: {detail_resp.text}"
        print("[DEBUG] trip_stops en detalle:",
              detail_resp.json().get("trip_stops"))

        # 9. Obtener las paradas del viaje
        stops_resp = client.get(
            f"/trip-stops/{client_request_id}/stops", headers=driver_headers)
        print("[DEBUG] Paradas del viaje:",
              stops_resp.status_code, stops_resp.text)
        assert stops_resp.status_code == 200, f"No se encontraron paradas: {stops_resp.text}"
        stops = stops_resp.json()
        assert len(stops) == 4, f"Cantidad de paradas inesperada: {len(stops)}"

        # 10. Marcar cada parada como completed en orden
        for stop in stops:
            complete_resp = client.patch(
                f"/trip-stops/{stop['id']}/status",
                json={"status": "COMPLETED"},
                headers=driver_headers)
            print(f"[DEBUG] Completar parada {stop['id']}:",
                  complete_resp.status_code, complete_resp.text)
            assert complete_resp.status_code == 200, f"Error al completar parada: {complete_resp.text}"
            assert complete_resp.json()["stop"]["status"] == "COMPLETED"

        # 11. Cambiar estado a FINISHED
        status_data = {"id_client_request": client_request_id,
                       "status": "FINISHED"}
        status_resp = client.patch(
            "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
        print("[DEBUG] Estado FINISHED:",
              status_resp.status_code, status_resp.text)
        assert status_resp.status_code == 200, f"Error FINISHED: {status_resp.text}"
        assert status_resp.json()["success"] is True

        # 12. Cambiar estado a PAID
        status_data = {
            "id_client_request": client_request_id, "status": "PAID"}
        status_resp = client.patch(
            "/client-request/updateStatusByDriver", json=status_data, headers=driver_headers)
        print("[DEBUG] Estado PAID:", status_resp.status_code, status_resp.text)
        assert status_resp.status_code == 200, f"Error PAID: {status_resp.text}"
        assert status_resp.json()["success"] is True

        # 13. Verificar que todas las paradas están completed y el viaje está PAID
        stops_resp = client.get(
            f"/trip-stops/{client_request_id}/stops", headers=driver_headers)
        print("[DEBUG] Paradas finales:",
              stops_resp.status_code, stops_resp.text)
        assert stops_resp.status_code == 200, f"No se encontraron paradas finales: {stops_resp.text}"
        stops = stops_resp.json()
        for stop in stops:
            assert stop["status"] == "COMPLETED", f"Parada no completada: {stop}"
        detail_resp = client.get(
            f"/client-request/{client_request_id}", headers=driver_headers)
        print("[DEBUG] Estado final del viaje:",
              detail_resp.status_code, detail_resp.text)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == str(StatusEnum.PAID)
    except Exception as e:
        print("[TRACEBACK] Error en el test:")
        traceback.print_exc()
        raise


def test_nearby_requests_include_trip_stops():
    """
    Test para verificar que las solicitudes cercanas incluyen información de paradas
    """
    # 1. Crear y autenticar cliente
    client_phone = "3000000001"
    client_country_code = "+57"
    client_token, client_id = create_and_approve_client(
        client, client_phone, client_country_code)
    headers = {"Authorization": f"Bearer {client_token}"}

    # 2. Crear solicitud de viaje con paradas intermedias
    request_data = {
        "fare_offered": 25000,
        "pickup_description": "Casa del cliente",
        "destination_description": "Centro comercial",
        "pickup_lat": 4.700000,
        "pickup_lng": -74.100000,
        "destination_lat": 4.710000,
        "destination_lng": -74.110000,
        "type_service_id": 1,
        "payment_method_id": 1,
        "intermediate_stops": [
            {"latitude": 4.705000, "longitude": -74.105000,
                "description": "Banco"},
            {"latitude": 4.707000, "longitude": -74.108000,
                "description": "Farmacia"}
        ]
    }
    create_resp = client.post(
        "/client-request/", json=request_data, headers=headers)
    assert create_resp.status_code == 201, f"Error al crear solicitud: {create_resp.text}"
    client_request_id = create_resp.json()["id"]

    # 3. Crear y aprobar conductor
    driver_phone = "3010000001"
    driver_country_code = "+57"
    driver_token, driver_id = create_and_approve_driver(
        client, driver_phone, driver_country_code)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    # 4. Buscar solicitudes cercanas como conductor
    nearby_resp = client.get(
        f"/client-request/nearby?driver_lat=4.700000&driver_lng=-74.100000",
        headers=driver_headers)
    print("[DEBUG] Solicitudes cercanas:",
          nearby_resp.status_code, nearby_resp.text)
    assert nearby_resp.status_code == 200, f"Error al buscar solicitudes cercanas: {nearby_resp.text}"

    nearby_data = nearby_resp.json()
    assert len(nearby_data) > 0, "No se encontraron solicitudes cercanas"

    # 5. Verificar que la solicitud incluye información de paradas
    found_request = None
    for request in nearby_data:
        if request["id"] == client_request_id:
            found_request = request
            break

    assert found_request is not None, "No se encontró la solicitud creada en las cercanas"
    assert "trip_stops" in found_request, "La solicitud no incluye información de paradas"
    assert len(found_request["trip_stops"]
               ) == 4, f"Se esperaban 4 paradas, se encontraron {len(found_request['trip_stops'])}"

    # Verificar que las paradas están en el orden correcto
    stops = found_request["trip_stops"]
    assert stops[0]["stop_type"] == "PICKUP", "Primera parada debe ser PICKUP"
    assert stops[1]["stop_type"] == "INTERMEDIATE", "Segunda parada debe ser INTERMEDIATE"
    assert stops[2]["stop_type"] == "INTERMEDIATE", "Tercera parada debe ser INTERMEDIATE"
    assert stops[3]["stop_type"] == "DESTINATION", "Cuarta parada debe ser DESTINATION"

    print("[DEBUG] ✅ Test passed: Las solicitudes cercanas incluyen información de paradas")
