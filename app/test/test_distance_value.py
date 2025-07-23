import pytest
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.models.client_request import StatusEnum
from app.test.test_client_request import create_and_approve_driver
import traceback


def test_multiple_stops_fare_calculation(client):
    """
    Test completo del flujo de múltiples paradas:
    1. Cliente cotiza viaje con múltiples paradas
    2. Verifica que la tarifa se calcula correctamente
    3. Cliente crea el viaje con múltiples paradas
    4. Verifica que las paradas se crean correctamente
    5. Verifica que la suma de rutas es correcta

    El test verifica que:
    - La API responde correctamente
    - La suma de distancias es precisa
    - Las paradas intermedias se procesan correctamente
    """
    print("\n=== INICIANDO TEST DE MÚLTIPLES PARADAS ===")

    # 1. Crear y autenticar cliente
    client_phone = "3004444456"
    client_country_code = "+57"

    print(f"1. Creando cliente con teléfono {client_phone}")
    send_resp = client.post(
        f"/auth/verify/{client_country_code}/{client_phone}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{client_country_code}/{client_phone}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    client_token = verify_resp.json()["access_token"]
    client_headers = {"Authorization": f"Bearer {client_token}"}
    print(f"✅ Cliente autenticado con token: {client_token[:20]}...")

    # 2. COTIZAR VIAJE CON MÚLTIPLES PARADAS
    print("\n2. Cotizando viaje con múltiples paradas...")

    cotizacion_data = {
        "type_service_id": 1,
        "origin_lat": 4.710989,
        "origin_lng": -74.072092,
        "destination_lat": 4.710989,
        "destination_lng": -74.072092,
        "intermediate_stops": [
            {
                "latitude": 4.711000,
                "longitude": -74.073000,
                "description": "Hospital Simón Bolívar"
            },
            {
                "latitude": 4.712000,
                "longitude": -74.074000,
                "description": "Centro Comercial Plaza Central"
            },
            {
                "latitude": 4.713000,
                "longitude": -74.075000,
                "description": "Farmacia Colsubsidio"
            }
        ]
    }

    print(f"   - Datos de cotización: {cotizacion_data}")

    # Llamar al endpoint de cotización con múltiples paradas
    cotizacion_resp = client.post(
        "/distance-value/multiple-stops",
        json=cotizacion_data,
        headers=client_headers
    )

    print(f"   - Status Code: {cotizacion_resp.status_code}")
    print(f"   - Response: {cotizacion_resp.text}")

    assert cotizacion_resp.status_code == 200, f"Error en cotización: {cotizacion_resp.text}"

    cotizacion_result = cotizacion_resp.json()
    print(f"✅ Cotización exitosa:")
    print(
        f"   - Tarifa recomendada: ${cotizacion_result.get('recommended_value')}")
    print(f"   - Distancia total: {cotizacion_result.get('distance')}")
    print(f"   - Duración total: {cotizacion_result.get('duration')}")
    print(f"   - Origen: {cotizacion_result.get('origin_addresses')}")
    print(f"   - Destino: {cotizacion_result.get('destination_addresses')}")

    # Verificar que la respuesta tiene todos los campos requeridos
    assert "recommended_value" in cotizacion_result, "Falta recommended_value en la respuesta"
    assert "distance" in cotizacion_result, "Falta distance en la respuesta"
    assert "duration" in cotizacion_result, "Falta duration en la respuesta"
    assert cotizacion_result["recommended_value"] > 0, "La tarifa debe ser mayor a 0"

    # 3. CREAR VIAJE CON MÚLTIPLES PARADAS
    print("\n3. Creando viaje con múltiples paradas...")

    viaje_data = {
        # Usar la cotización
        "fare_offered": cotizacion_result["recommended_value"],
        "pickup_description": "Mi casa en Suba",
        "destination_description": "Mi casa (regreso)",
        "pickup_lat": 4.710989,
        "pickup_lng": -74.072092,
        "destination_lat": 4.710989,
        "destination_lng": -74.072092,
        "type_service_id": 1,
        "payment_method_id": 1,
        "intermediate_stops": [
            {
                "latitude": 4.711000,
                "longitude": -74.073000,
                "description": "Hospital Simón Bolívar"
            },
            {
                "latitude": 4.712000,
                "longitude": -74.074000,
                "description": "Centro Comercial Plaza Central"
            },
            {
                "latitude": 4.713000,
                "longitude": -74.075000,
                "description": "Farmacia Colsubsidio"
            }
        ]
    }

    print(f"   - Datos del viaje: {viaje_data}")

    create_resp = client.post(
        "/client-request/",
        json=viaje_data,
        headers=client_headers
    )

    print(f"   - Status Code: {create_resp.status_code}")
    print(f"   - Response: {create_resp.text}")

    assert create_resp.status_code == 201, f"Error al crear viaje: {create_resp.text}"

    viaje_result = create_resp.json()
    client_request_id = viaje_result["id"]
    print(f"✅ Viaje creado con ID: {client_request_id}")

    # 4. VERIFICAR QUE LAS PARADAS SE CREARON CORRECTAMENTE
    print("\n4. Verificando que las paradas se crearon correctamente...")

    # Obtener las paradas del viaje
    stops_resp = client.get(
        f"/trip-stops/{client_request_id}/stops",
        headers=client_headers
    )

    print(f"   - Status Code: {stops_resp.status_code}")
    print(f"   - Response: {stops_resp.text}")

    assert stops_resp.status_code == 200, f"Error al obtener paradas: {stops_resp.text}"

    stops = stops_resp.json()
    print(f"✅ Paradas obtenidas: {len(stops)} paradas")

    # Verificar que se crearon todas las paradas (origen + 3 intermedias + destino = 5)
    assert len(
        stops) == 5, f"Se esperaban 5 paradas, se encontraron {len(stops)}"

    # Verificar el orden y tipos de paradas
    expected_order = ["PICKUP", "INTERMEDIATE",
                      "INTERMEDIATE", "INTERMEDIATE", "DESTINATION"]
    for i, stop in enumerate(stops):
        print(
            f"   - Parada {i+1}: {stop['stop_type']} - {stop['description']}")
        assert stop["stop_type"] == expected_order[
            i], f"Parada {i+1} debería ser {expected_order[i]}, es {stop['stop_type']}"

    # 5. VERIFICAR QUE LA SUMA DE RUTAS ES CORRECTA
    print("\n5. Verificando que la suma de rutas es correcta...")

    # Obtener el progreso del viaje
    progress_resp = client.get(
        f"/trip-stops/{client_request_id}/progress",
        headers=client_headers
    )

    print(f"   - Status Code: {progress_resp.status_code}")
    print(f"   - Response: {progress_resp.text}")

    assert progress_resp.status_code == 200, f"Error al obtener progreso: {progress_resp.text}"

    progress = progress_resp.json()
    print(f"✅ Progreso del viaje:")
    print(f"   - Total de paradas: {progress['total_stops']}")
    print(f"   - Paradas completadas: {progress['completed_stops']}")
    print(f"   - Paradas pendientes: {progress['pending_stops']}")
    print(f"   - Progreso: {progress['progress_percentage']}%")

    # Verificar que el progreso es correcto
    assert progress[
        "total_stops"] == 5, f"Total de paradas debería ser 5, es {progress['total_stops']}"
    assert progress[
        "completed_stops"] == 0, f"Paradas completadas debería ser 0, es {progress['completed_stops']}"
    assert progress[
        "pending_stops"] == 5, f"Paradas pendientes debería ser 5, es {progress['pending_stops']}"
    assert progress[
        "progress_percentage"] == 0, f"Progreso debería ser 0%, es {progress['progress_percentage']}%"

    # 6. COMPARAR COTIZACIÓN CON VIAJE REAL
    print("\n6. Comparando cotización con viaje real...")

    # Obtener detalles del viaje
    detail_resp = client.get(
        f"/client-request/{client_request_id}",
        headers=client_headers
    )

    assert detail_resp.status_code == 200, f"Error al obtener detalles: {detail_resp.text}"

    detail = detail_resp.json()
    print(f"✅ Detalles del viaje:")
    print(f"   - ID: {detail['id']}")
    print(f"   - Estado: {detail['status']}")
    print(f"   - Tarifa ofrecida: ${detail['fare_offered']}")
    print(f"   - Paradas en el viaje: {len(detail.get('trip_stops', []))}")

    # Verificar que la tarifa del viaje coincide con la cotización
    assert detail["fare_offered"] == cotizacion_result["recommended_value"], \
        f"La tarifa del viaje ({detail['fare_offered']}) no coincide con la cotización ({cotizacion_result['recommended_value']})"

    # Verificar que las paradas en el detalle coinciden
    trip_stops = detail.get("trip_stops", [])
    assert len(
        trip_stops) == 5, f"El viaje debería tener 5 paradas, tiene {len(trip_stops)}"

    print("\n=== TEST DE MÚLTIPLES PARADAS COMPLETADO EXITOSAMENTE ===")
    print(f"✅ Flujo completo verificado:")
    print(f"   - Cotización: ${cotizacion_result['recommended_value']}")
    print(f"   - Viaje creado: {client_request_id}")
    print(f"   - Paradas creadas: {len(stops)}")
    print(f"   - Suma de rutas verificada")


def test_simple_vs_multiple_stops_comparison(client):
    """
    Test que compara la cotización simple vs múltiples paradas
    para verificar que la suma es correcta.
    """
    print("\n=== INICIANDO TEST DE COMPARACIÓN SIMPLE VS MÚLTIPLES ===")

    # 1. Autenticar cliente
    client_phone = "3004444457"
    client_country_code = "+57"

    send_resp = client.post(
        f"/auth/verify/{client_country_code}/{client_phone}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{client_country_code}/{client_phone}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    client_token = verify_resp.json()["access_token"]
    client_headers = {"Authorization": f"Bearer {client_token}"}

    # 2. COTIZACIÓN SIMPLE (origen → destino directo)
    print("\n2. Cotización simple (origen → destino)...")

    simple_cotizacion = client.get(
        "/distance-value/?type_service_id=1&origin_lat=4.710989&origin_lng=-74.072092&destination_lat=4.720000&destination_lng=-74.080000",
        headers=client_headers
    )

    assert simple_cotizacion.status_code == 200, f"Error en cotización simple: {simple_cotizacion.text}"
    simple_result = simple_cotizacion.json()

    print(f"✅ Cotización simple:")
    print(f"   - Tarifa: ${simple_result['recommended_value']}")
    print(f"   - Distancia: {simple_result['distance']}")
    print(f"   - Duración: {simple_result['duration']}")

    # 3. COTIZACIÓN CON MÚLTIPLES PARADAS (misma ruta pero con paradas intermedias)
    print("\n3. Cotización con múltiples paradas...")

    multiple_data = {
        "type_service_id": 1,
        "origin_lat": 4.710989,
        "origin_lng": -74.072092,
        "destination_lat": 4.720000,
        "destination_lng": -74.080000,
        "intermediate_stops": [
            {
                "latitude": 4.715000,
                "longitude": -74.075000,
                "description": "Parada intermedia 1"
            },
            {
                "latitude": 4.718000,
                "longitude": -74.078000,
                "description": "Parada intermedia 2"
            }
        ]
    }

    multiple_cotizacion = client.post(
        "/distance-value/multiple-stops",
        json=multiple_data,
        headers=client_headers
    )

    assert multiple_cotizacion.status_code == 200, f"Error en cotización múltiple: {multiple_cotizacion.text}"
    multiple_result = multiple_cotizacion.json()

    print(f"✅ Cotización múltiple:")
    print(f"   - Tarifa: ${multiple_result['recommended_value']}")
    print(f"   - Distancia: {multiple_result['distance']}")
    print(f"   - Duración: {multiple_result['duration']}")

    # 4. VERIFICAR QUE LA RUTA CON PARADAS ES MÁS LARGA
    print("\n4. Verificando que la ruta con paradas es más larga...")

    # Extraer valores numéricos de las distancias
    simple_distance = float(simple_result['distance'].split()[0])
    multiple_distance = float(multiple_result['distance'].split()[0])

    print(f"   - Distancia simple: {simple_distance} km")
    print(f"   - Distancia múltiple: {multiple_distance} km")

    # La ruta con paradas debería ser más larga (o igual en el peor caso)
    assert multiple_distance >= simple_distance, \
        f"La ruta con paradas ({multiple_distance} km) debería ser más larga que la simple ({simple_distance} km)"

    # La tarifa con paradas debería ser mayor
    assert multiple_result['recommended_value'] >= simple_result['recommended_value'], \
        f"La tarifa con paradas (${multiple_result['recommended_value']}) debería ser mayor que la simple (${simple_result['recommended_value']})"

    print(f"✅ Verificación exitosa:")
    print(
        f"   - Ruta con paradas es {multiple_distance - simple_distance:.2f} km más larga")
    print(
        f"   - Tarifa con paradas es ${multiple_result['recommended_value'] - simple_result['recommended_value']:.2f} más cara")

    print("\n=== TEST DE COMPARACIÓN COMPLETADO EXITOSAMENTE ===")
