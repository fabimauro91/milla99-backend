import random
import time
from locust import HttpUser, task, between, events
from typing import Dict


class UserCreationOnlyTest(HttpUser):
    """
    Test de carga optimizado SOLO para creación de usuarios
    Enfoque: POST /users/ para medir 3000 requests/minuto
    """

    # Tiempo de espera muy bajo para alta carga
    wait_time = between(0.05, 0.2)

    def on_start(self):
        """Inicialización del usuario virtual"""
        print(f"Iniciando usuario virtual para creación de usuarios")

    @task(1)
    def create_user_only(self):
        """Crear usuario - única tarea para máxima carga"""

        # Generar datos únicos que cumplan con las validaciones
        timestamp = int(time.time() * 1000) % 1000000
        # 7 dígitos para tener 10 caracteres total
        phone_suffix = random.randint(1000000, 9999999)
        # 10 caracteres: 300 + 7 dígitos
        phone_number = f"300{phone_suffix}"

        nombres = ["Juan", "María", "Carlos", "Ana", "Luis",
                   "Sofia", "Diego", "Valentina", "Andrés", "Camila"]
        apellidos = ["García", "Rodríguez", "López", "Martínez",
                     "González", "Pérez", "Sánchez", "Ramírez", "Torres", "Flores"]

        nombre = random.choice(nombres)
        apellido = random.choice(apellidos)
        # Solo letras y espacios, sin números
        full_name = f"{nombre} {apellido}"

        user_data = {
            "full_name": full_name,
            "country_code": "+57",
            "phone_number": phone_number,
            "referral_phone": None
        }

        try:
            response = self.client.post(
                "/users/",
                json=user_data,
                name="Create User Only"
            )

            if response.status_code == 201:
                print(f"[SUCCESS] Usuario creado: {phone_number}")
            elif response.status_code == 409:
                print(f"[INFO] Usuario ya existe: {phone_number}")
            else:
                print(f"[ERROR] {response.status_code}: {response.text}")

        except Exception as e:
            print(f"[ERROR] Exception: {e}")


@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Manejador de eventos para requests fallidos"""
    if exception:
        print(f"[ERROR] Request failed: {name} - {exception}")
    elif response and response.status_code >= 400:
        print(
            f"[ERROR] Request failed: {name} - Status: {response.status_code}")


class LoadTestConfig:
    """
    Configuración optimizada para 3000 requests/minuto
    """

    # Configuración de usuarios
    USERS = 300  # Más usuarios para alcanzar el objetivo
    SPAWN_RATE = 100  # Spawn muy rápido

    # Configuración de tiempo
    RUN_TIME = "60s"  # 1 minuto de prueba

    # Configuración de host
    HOST = "http://localhost:8000"

    # Umbrales de performance para 3000 requests/minuto
    PERFORMANCE_THRESHOLDS = {
        "response_time_p95": 2000,  # 2 segundos
        "response_time_p99": 5000,  # 5 segundos
        "failure_rate": 5.0,  # 5%
        "requests_per_sec": 50  # 50 requests por segundo = 3000/minuto
    }


if __name__ == "__main__":
    """
    Para ejecutar directamente:
    python -m locust -f app/load_tests/locust/load_user_creation_only.py --host=http://localhost:8000
    """
    print("Test de carga optimizado SOLO para creación de usuarios")
    print(f"Objetivo: 3000 requests/minuto")
    print(f"Usuarios: {LoadTestConfig.USERS}")
    print(f"Spawn rate: {LoadTestConfig.SPAWN_RATE}")
    print(f"Tiempo: {LoadTestConfig.RUN_TIME}")
    print("\nPara ejecutar:")
    print("locust -f app/load_tests/locust/load_user_creation_only.py --host=http://localhost:8000")
