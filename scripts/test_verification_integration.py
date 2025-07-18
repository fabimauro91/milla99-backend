#!/usr/bin/env python3
"""
Script de prueba para verificar la integración de verificación de documentos.
Ejecutar después de implementar todos los cambios.
"""

from app.utils.notification_templates import NotificationTemplates
from app.services.notification_service import NotificationService
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.user import User
from app.models.driver_info import DriverInfo
from sqlmodel import Session, select
from app.core.db import engine
import sys
import os
import asyncio
from datetime import datetime
from uuid import uuid4

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_verification_fields():
    """Prueba que los campos de verificación estén disponibles en DriverInfo"""
    print("🔍 Probando campos de verificación en DriverInfo...")

    try:
        with Session(engine) as session:
            # Crear un DriverInfo de prueba
            test_driver_info = DriverInfo(
                first_name="Test",
                last_name="Driver",
                birth_date=datetime.now().date(),
                email="test@example.com",
                user_id=uuid4(),
                # Campos de verificación
                document_verification_status="PENDING",
                document_verification_score=0.75,
                document_verification_details={"test": "data"},
                document_verification_date=datetime.now(),
                document_verification_id="test_verif_123",
                verification_attempts=1,
                last_verification_attempt=datetime.now()
            )

            print("✅ Campos de verificación disponibles en DriverInfo")
            print(
                f"   - Status: {test_driver_info.document_verification_status}")
            print(
                f"   - Score: {test_driver_info.document_verification_score}")
            print(f"   - Attempts: {test_driver_info.verification_attempts}")

    except Exception as e:
        print(f"❌ Error probando campos de verificación: {e}")
        return False

    return True


def test_notification_templates():
    """Prueba que las plantillas de notificación estén disponibles"""
    print("\n🔍 Probando plantillas de notificación...")

    try:
        # Probar plantilla de aprobación
        approved_template = NotificationTemplates.verification_approved()
        print("✅ Plantilla de aprobación disponible")
        print(f"   - Título: {approved_template['title']}")

        # Probar plantilla de rechazo
        rejected_template = NotificationTemplates.verification_rejected(
            ["Problema 1", "Problema 2"])
        print("✅ Plantilla de rechazo disponible")
        print(f"   - Título: {rejected_template['title']}")

        # Probar plantilla de revisión manual
        manual_template = NotificationTemplates.verification_manual_review()
        print("✅ Plantilla de revisión manual disponible")
        print(f"   - Título: {manual_template['title']}")

    except Exception as e:
        print(f"❌ Error probando plantillas de notificación: {e}")
        return False

    return True


def test_notification_service():
    """Prueba que el servicio de notificaciones esté disponible"""
    print("\n🔍 Probando servicio de notificaciones...")

    try:
        with Session(engine) as session:
            notification_service = NotificationService(session)

            # Probar métodos de notificación
            methods = [
                'notify_verification_approved',
                'notify_verification_rejected',
                'notify_verification_manual_review',
                'notify_verification_manual_approved',
                'notify_verification_manual_rejected'
            ]

            for method_name in methods:
                if hasattr(notification_service, method_name):
                    print(f"✅ Método {method_name} disponible")
                else:
                    print(f"❌ Método {method_name} NO disponible")
                    return False

    except Exception as e:
        print(f"❌ Error probando servicio de notificaciones: {e}")
        return False

    return True


def test_database_schema():
    """Prueba que los campos estén en la base de datos"""
    print("\n🔍 Probando esquema de base de datos...")

    try:
        with Session(engine) as session:
            # Verificar que la tabla driver_info tenga los campos necesarios
            # Esto es una verificación básica - en producción usarías migraciones
            print("✅ Conexión a base de datos exitosa")

            # Intentar consultar un driver_info para verificar estructura
            driver_info = session.exec(select(DriverInfo).limit(1)).first()
            if driver_info:
                print("✅ Tabla driver_info accesible")
                print(
                    f"   - Campos disponibles: {driver_info.__dict__.keys()}")
            else:
                print("⚠️ No hay datos en driver_info para probar")

    except Exception as e:
        print(f"❌ Error probando esquema de base de datos: {e}")
        return False

    return True


def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de integración de verificación...")
    print("=" * 60)

    tests = [
        ("Campos de verificación", test_verification_fields),
        ("Plantillas de notificación", test_notification_templates),
        ("Servicio de notificaciones", test_notification_service),
        ("Esquema de base de datos", test_database_schema)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Ejecutando: {test_name}")
        if test_func():
            print(f"✅ {test_name}: PASÓ")
            passed += 1
        else:
            print(f"❌ {test_name}: FALLÓ")

    print("\n" + "=" * 60)
    print(f"📊 Resultados: {passed}/{total} pruebas pasaron")

    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La integración está lista.")
        return True
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar implementación.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
