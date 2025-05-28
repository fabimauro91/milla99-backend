import requests
import json
from datetime import datetime
from app.core.config import settings
import jwt
from app.models.client_request import StatusEnum
from app.models.type_service import TypeService
from app.models.vehicle_type import VehicleType
from sqlmodel import Session, select
from app.core.db import engine

# URLs base
BASE_URL = "http://localhost:8000"
NEARBY_URL = f"{BASE_URL}/client-request/nearby"

# Coordenadas de prueba (Bogotá)
TEST_COORDINATES = {
    "driver": {
        "lat": 4.708822,
        "lng": -74.076542
    },
    "pickup": {
        "lat": 4.718136,
        "lng": -74.073170
    },
    "destination": {
        "lat": 4.702468,
        "lng": -74.109776
    }
}


def create_test_token(user_id: int, role: str) -> str:
    """Crea un token JWT para pruebas"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow().timestamp() + 3600
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def get_user_id_by_phone(phone: str) -> int:
    """Obtiene el ID de usuario por número de teléfono"""
    with Session(engine) as session:
        from app.models.user import User
        user = session.exec(select(User).where(
            User.phone_number == phone)).first()
        return user.id if user else None


def get_type_service_id(vehicle_type: str) -> int:
    """Obtiene el ID del tipo de servicio por tipo de vehículo"""
    with Session(engine) as session:
        type_service = session.exec(
            select(TypeService)
            .join(VehicleType)
            .where(VehicleType.name == vehicle_type)
        ).first()
        return type_service.id if type_service else None


def create_client_request(client_phone: str, type_service_id: int) -> dict:
    """Crea una solicitud de viaje para un cliente"""
    client_id = get_user_id_by_phone(client_phone)
    if not client_id:
        raise Exception(f"Cliente no encontrado: {client_phone}")

    token = create_test_token(client_id, "CLIENT")
    headers = {"Authorization": f"Bearer {token}"}

    request_data = {
        "fare_offered": 20000,
        "pickup_description": "Suba Bogotá",
        "destination_description": "Santa Rosita Engativa, Bogota",
        "pickup_lat": TEST_COORDINATES["pickup"]["lat"],
        "pickup_lng": TEST_COORDINATES["pickup"]["lng"],
        "destination_lat": TEST_COORDINATES["destination"]["lat"],
        "destination_lng": TEST_COORDINATES["destination"]["lng"],
        "type_service_id": type_service_id
    }

    response = requests.post(
        f"{BASE_URL}/client-request/",
        headers=headers,
        json=request_data
    )

    if response.status_code != 201:
        raise Exception(f"Error creando solicitud: {response.text}")

    return response.json()


def test_nearby_with_driver(driver_phone: str):
    """Prueba el endpoint /nearby con un conductor específico"""
    driver_id = get_user_id_by_phone(driver_phone)
    if not driver_id:
        raise Exception(f"Conductor no encontrado: {driver_phone}")

    token = create_test_token(driver_id, "DRIVER")
    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "driver_lat": TEST_COORDINATES["driver"]["lat"],
        "driver_lng": TEST_COORDINATES["driver"]["lng"]
    }

    response = requests.get(NEARBY_URL, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Error en /nearby: {response.text}")

    return response.json()


def run_nearby_test():
    """Ejecuta la prueba completa del endpoint /nearby"""
    print("\n=== Iniciando prueba de /nearby ===\n")

    # 1. Obtener IDs de tipos de servicio
    car_service_id = get_type_service_id("Car")
    moto_service_id = get_type_service_id("Motorcycle")

    if not car_service_id or not moto_service_id:
        raise Exception("No se encontraron los tipos de servicio")

    print("1. Creando solicitudes de viaje...")

    # 2. Crear solicitudes de viaje
    # Solicitudes para carro
    car_request1 = create_client_request(
        "3001111111", car_service_id)  # María García
    print(f"Solicitud de carro creada para María García: {car_request1['id']}")

    car_request2 = create_client_request(
        "3002222222", car_service_id)  # Juan Pérez
    print(f"Solicitud de carro creada para Juan Pérez: {car_request2['id']}")

    # Solicitudes para moto
    moto_request1 = create_client_request(
        "3004444459", moto_service_id)  # Ana Martínez
    print(f"Solicitud de moto creada para Ana Martínez: {moto_request1['id']}")

    moto_request2 = create_client_request(
        "3004444460", moto_service_id)  # Carlos Rodríguez
    print(
        f"Solicitud de moto creada para Carlos Rodríguez: {moto_request2['id']}")

    print("\n2. Probando endpoint /nearby con conductores...")

    # 3. Probar con conductor de carro
    print("\nProbando con conductor de carro (Roberto Sánchez):")
    car_driver_results = test_nearby_with_driver("3005555555")
    if isinstance(car_driver_results, dict) and "data" in car_driver_results:
        car_requests = car_driver_results["data"]
    else:
        car_requests = car_driver_results
    print(f"Solicitudes encontradas: {len(car_requests)}")
    for req in car_requests:
        print(
            f"- Solicitud {req['id']}: Tipo de servicio {req.get('type_service_id')}")

    # 4. Probar con conductor de moto
    print("\nProbando con conductor de moto (Pedro Gómez):")
    moto_driver_results = test_nearby_with_driver("3007777777")
    if isinstance(moto_driver_results, dict) and "data" in moto_driver_results:
        moto_requests = moto_driver_results["data"]
    else:
        moto_requests = moto_driver_results
    print(f"Solicitudes encontradas: {len(moto_requests)}")
    for req in moto_requests:
        print(
            f"- Solicitud {req['id']}: Tipo de servicio {req.get('type_service_id')}")

    # 5. Verificar resultados
    print("\n=== Resultados de la prueba ===")
    print("\nConductor de carro debería ver solo solicitudes de carro:")
    car_service_requests = [req for req in car_requests if req.get(
        'type_service_id') == car_service_id]
    print(f"- Solicitudes de carro encontradas: {len(car_service_requests)}")
    print(f"- Total de solicitudes encontradas: {len(car_requests)}")

    print("\nConductor de moto debería ver solo solicitudes de moto:")
    moto_service_requests = [req for req in moto_requests if req.get(
        'type_service_id') == moto_service_id]
    print(f"- Solicitudes de moto encontradas: {len(moto_service_requests)}")
    print(f"- Total de solicitudes encontradas: {len(moto_requests)}")


if __name__ == "__main__":
    run_nearby_test()
