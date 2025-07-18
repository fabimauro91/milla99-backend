#!/usr/bin/env python3
"""
Script de prueba para el flujo completo de verificación de documentos.
Prueba el registro de driver, verificación automática, consulta de estado y notificaciones.
"""

import sys
import os
import asyncio
import requests
import json
from datetime import datetime
from uuid import uuid4

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración
BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = ""


class VerificationFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_user_id = None
        self.test_driver_info_id = None
        self.access_token = None

    def print_step(self, step_name: str):
        """Imprime un paso del test con formato"""
        print(f"\n{'='*60}")
        print(f"🔍 PASO: {step_name}")
        print(f"{'='*60}")

    def print_success(self, message: str):
        """Imprime un mensaje de éxito"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """Imprime un mensaje de error"""
        print(f"❌ {message}")

    def print_info(self, message: str):
        """Imprime información"""
        print(f"ℹ️ {message}")

    def test_server_connection(self):
        """Prueba que el servidor esté funcionando"""
        self.print_step("CONECTANDO AL SERVIDOR")

        try:
            response = self.session.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                self.print_success("Servidor funcionando correctamente")
                return True
            else:
                self.print_error(
                    f"Servidor no responde correctamente: {response.status_code}")
                return False
        except Exception as e:
            self.print_error(f"No se puede conectar al servidor: {e}")
            return False

    def test_driver_registration_flow(self):
        """Prueba el flujo de registro de driver"""
        self.print_step("REGISTRO DE DRIVER")

        # Datos de prueba para el driver
        user_data = {
            "full_name": "Test Driver",
            "country_code": "+57",
            "phone_number": f"300{str(uuid4().int)[:8]}",
            "password": "testpassword123"
        }

        driver_info_data = {
            "first_name": "Test",
            "last_name": "Driver",
            "birth_date": "1990-01-01",
            "email": f"test.driver.{uuid4().hex[:8]}@example.com"
        }

        vehicle_info_data = {
            "brand": "Toyota",
            "model": "Corolla",
            "model_year": 2020,
            "color": "Blanco",
            "plate": f"ABC{str(uuid4().int)[:6]}",
            "vehicle_type_id": 1
        }

        driver_documents_data = {
            "license_expiration_date": "2025-12-31",
            "soat_expiration_date": "2025-12-31",
            "vehicle_technical_inspection_expiration_date": "2025-12-31"
        }

        try:
            # Crear archivos de prueba
            import io

            # Crear una imagen de prueba simple
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf5\x8d\xb0\xfd\x00\x00\x00\x00IEND\xaeB`\x82'

            # Registrar driver con Form data
            files = {
                'selfie': ('test_selfie.png', io.BytesIO(test_image_data), 'image/png')
            }

            data = {
                'user': json.dumps(user_data),
                'driver_info': json.dumps(driver_info_data),
                'vehicle_info': json.dumps(vehicle_info_data),
                'driver_documents': json.dumps(driver_documents_data)
            }

            url = f"{BASE_URL}{API_PREFIX}/drivers"
            print(f"🔍 DEBUG: Haciendo POST a: {url}")
            print(f"🔍 DEBUG: Data: {data}")
            print(f"🔍 DEBUG: Files: {files}")

            response = self.session.post(
                url,
                data=data,
                files=files
            )

            if response.status_code == 201:
                result = response.json()
                self.test_user_id = result.get("user_id")
                self.test_driver_info_id = result.get("driver_info_id")
                self.print_success(f"Driver registrado exitosamente")
                self.print_info(f"User ID: {self.test_user_id}")
                self.print_info(f"Driver Info ID: {self.test_driver_info_id}")
                return True
            else:
                self.print_error(
                    f"Error registrando driver: {response.status_code}")
                self.print_error(f"Respuesta: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Error en registro de driver: {e}")
            return False

    def test_verification_status_endpoint(self):
        """Prueba el endpoint de consulta de estado de verificación"""
        self.print_step("CONSULTA DE ESTADO DE VERIFICACIÓN")

        if not self.test_user_id:
            self.print_error("No hay user_id para probar")
            return False

        try:
            # Primero necesitamos autenticarnos
            auth_response = self.session.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={
                    "phone_number": f"300{str(uuid4().int)[:8]}",
                    "password": "testpassword123"
                }
            )

            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                self.access_token = auth_data.get("access_token")

                # Consultar estado de verificación
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = self.session.get(
                    f"{BASE_URL}{API_PREFIX}/document-verification/driver-status",
                    headers=headers
                )

                if response.status_code == 200:
                    status_data = response.json()
                    self.print_success(
                        "Estado de verificación consultado exitosamente")
                    self.print_info(
                        f"Status: {status_data.get('verification_status')}")
                    self.print_info(
                        f"Score: {status_data.get('verification_score')}")
                    self.print_info(
                        f"Can Operate: {status_data.get('can_operate')}")
                    return True
                else:
                    self.print_error(
                        f"Error consultando estado: {response.status_code}")
                    self.print_error(f"Respuesta: {response.text}")
                    return False
            else:
                self.print_error(
                    f"Error en autenticación: {auth_response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Error consultando estado: {e}")
            return False

    def test_admin_endpoints(self):
        """Prueba los endpoints administrativos"""
        self.print_step("ENDPOINTS ADMINISTRATIVOS")

        if not self.test_user_id:
            self.print_error("No hay user_id para probar")
            return False

        try:
            # Probar endpoint de aprobación manual
            approve_response = self.session.post(
                f"{BASE_URL}{API_PREFIX}/verify-docs/manual-approve-driver/{self.test_user_id}"
            )

            if approve_response.status_code == 200:
                self.print_success("Endpoint de aprobación manual funciona")
                approve_data = approve_response.json()
                self.print_info(
                    f"Nuevo status: {approve_data.get('new_status', {}).get('status')}")
            else:
                self.print_error(
                    f"Error en aprobación manual: {approve_response.status_code}")

            # Probar endpoint de rechazo manual
            reject_response = self.session.post(
                f"{BASE_URL}{API_PREFIX}/verify-docs/manual-reject-driver/{self.test_user_id}",
                params={"reason": "Prueba de rechazo manual"}
            )

            if reject_response.status_code == 200:
                self.print_success("Endpoint de rechazo manual funciona")
                reject_data = reject_response.json()
                self.print_info(
                    f"Razón de rechazo: {reject_data.get('rejection_reason')}")
            else:
                self.print_error(
                    f"Error en rechazo manual: {reject_response.status_code}")

            return True

        except Exception as e:
            self.print_error(f"Error probando endpoints administrativos: {e}")
            return False

    def test_notification_templates(self):
        """Prueba las plantillas de notificación"""
        self.print_step("PLANTILLAS DE NOTIFICACIÓN")

        try:
            from app.utils.notification_templates import NotificationTemplates

            # Probar plantilla de aprobación
            approved = NotificationTemplates.verification_approved()
            self.print_success("Plantilla de aprobación funciona")
            self.print_info(f"Título: {approved['title']}")

            # Probar plantilla de rechazo
            rejected = NotificationTemplates.verification_rejected(
                ["Problema 1", "Problema 2"])
            self.print_success("Plantilla de rechazo funciona")
            self.print_info(f"Título: {rejected['title']}")

            # Probar plantilla de revisión manual
            manual = NotificationTemplates.verification_manual_review()
            self.print_success("Plantilla de revisión manual funciona")
            self.print_info(f"Título: {manual['title']}")

            return True

        except Exception as e:
            self.print_error(f"Error probando plantillas: {e}")
            return False

    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        print("🚀 INICIANDO PRUEBAS DEL FLUJO DE VERIFICACIÓN")
        print("=" * 80)

        tests = [
            ("Conexión al servidor", self.test_server_connection),
            ("Plantillas de notificación", self.test_notification_templates),
            ("Registro de driver", self.test_driver_registration_flow),
            ("Consulta de estado", self.test_verification_status_endpoint),
            ("Endpoints administrativos", self.test_admin_endpoints)
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"⚠️ {test_name}: FALLÓ")
            except Exception as e:
                self.print_error(f"Error en {test_name}: {e}")

        print("\n" + "=" * 80)
        print(f"📊 RESULTADOS FINALES: {passed}/{total} pruebas pasaron")

        if passed == total:
            print(
                "🎉 ¡TODAS LAS PRUEBAS PASARON! El flujo está funcionando correctamente.")
        else:
            print("⚠️ Algunas pruebas fallaron. Revisar implementación.")

        return passed == total


def main():
    """Función principal"""
    tester = VerificationFlowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
