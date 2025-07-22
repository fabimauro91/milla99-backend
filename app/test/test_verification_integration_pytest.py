"""
Tests de Pytest para la integración de verificación de documentos.
Ejecutar con: pytest app/test/test_verification_integration_pytest.py -v
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4
from sqlmodel import Session, select

from app.core.db import engine
from app.models.driver_info import DriverInfo
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.services.notification_service import NotificationService
from app.utils.notification_templates import NotificationTemplates


class TestVerificationIntegration:
    """Tests para la integración de verificación de documentos"""

    @pytest.fixture
    def session(self):
        """Fixture para obtener una sesión de base de datos"""
        with Session(engine) as session:
            yield session

    @pytest.fixture
    def notification_service(self, session):
        """Fixture para el servicio de notificaciones"""
        return NotificationService(session)

    @pytest.fixture
    def test_driver_info(self):
        """Fixture para crear un DriverInfo de prueba"""
        return DriverInfo(
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

    def test_verification_fields_exist(self, test_driver_info):
        """Test: Verificar que los campos de verificación existen"""
        assert hasattr(test_driver_info, 'document_verification_status')
        assert hasattr(test_driver_info, 'document_verification_score')
        assert hasattr(test_driver_info, 'document_verification_details')
        assert hasattr(test_driver_info, 'document_verification_date')
        assert hasattr(test_driver_info, 'document_verification_id')
        assert hasattr(test_driver_info, 'verification_attempts')
        assert hasattr(test_driver_info, 'last_verification_attempt')

    def test_verification_fields_defaults(self, test_driver_info):
        """Test: Verificar valores por defecto de campos de verificación"""
        assert test_driver_info.document_verification_status == "PENDING"
        assert test_driver_info.document_verification_score == 0.75
        assert test_driver_info.verification_attempts == 1
        assert test_driver_info.document_verification_id == "test_verif_123"

    def test_notification_templates_exist(self):
        """Test: Verificar que las plantillas de notificación existen"""
        # Plantilla de aprobación
        approved = NotificationTemplates.verification_approved()
        assert approved is not None
        assert "title" in approved
        assert "body" in approved
        assert "data" in approved
        assert approved["title"] == "¡Verificación aprobada!"

        # Plantilla de rechazo
        rejected = NotificationTemplates.verification_rejected(["Problema 1"])
        assert rejected is not None
        assert "title" in rejected
        assert "body" in rejected
        assert "data" in rejected
        assert rejected["title"] == "Verificación rechazada"

        # Plantilla de revisión manual
        manual = NotificationTemplates.verification_manual_review()
        assert manual is not None
        assert "title" in manual
        assert "body" in manual
        assert "data" in manual
        assert manual["title"] == "Verificación en revisión"

    def test_notification_service_methods_exist(self, notification_service):
        """Test: Verificar que los métodos de notificación existen"""
        methods = [
            'notify_verification_approved',
            'notify_verification_rejected',
            'notify_verification_manual_review',
            'notify_verification_manual_approved',
            'notify_verification_manual_rejected'
        ]

        for method_name in methods:
            assert hasattr(notification_service, method_name)
            method = getattr(notification_service, method_name)
            assert callable(method)

    def test_notification_service_methods_return_dict(self, notification_service):
        """Test: Verificar que los métodos de notificación retornan diccionarios"""
        test_user_id = uuid4()

        # Probar método de aprobación
        result = notification_service.notify_verification_approved(
            test_user_id)
        assert isinstance(result, dict)
        assert "success" in result or "error" in result

        # Probar método de rechazo
        result = notification_service.notify_verification_rejected(test_user_id, [
                                                                   "Problema"])
        assert isinstance(result, dict)
        assert "success" in result or "error" in result

        # Probar método de revisión manual
        result = notification_service.notify_verification_manual_review(
            test_user_id)
        assert isinstance(result, dict)
        assert "success" in result or "error" in result

    def test_database_connection(self, session):
        """Test: Verificar conexión a base de datos"""
        # Intentar consultar un DriverInfo
        driver_info = session.exec(select(DriverInfo).limit(1)).first()
        # No importa si hay datos o no, solo verificar que la conexión funciona
        assert session is not None

    def test_verification_status_transitions(self, test_driver_info):
        """Test: Verificar transiciones de estado de verificación"""
        # Estado inicial
        assert test_driver_info.document_verification_status == "PENDING"

        # Transición a APPROVED
        test_driver_info.document_verification_status = "APPROVED"
        assert test_driver_info.document_verification_status == "APPROVED"

        # Transición a REJECTED
        test_driver_info.document_verification_status = "REJECTED"
        assert test_driver_info.document_verification_status == "REJECTED"

        # Transición a MANUAL_REVIEW
        test_driver_info.document_verification_status = "MANUAL_REVIEW"
        assert test_driver_info.document_verification_status == "MANUAL_REVIEW"

    def test_verification_score_range(self, test_driver_info):
        """Test: Verificar que el score de verificación está en rango válido"""
        # Score válido
        test_driver_info.document_verification_score = 0.85
        assert 0.0 <= test_driver_info.document_verification_score <= 1.0

        # Score mínimo
        test_driver_info.document_verification_score = 0.0
        assert test_driver_info.document_verification_score == 0.0

        # Score máximo
        test_driver_info.document_verification_score = 1.0
        assert test_driver_info.document_verification_score == 1.0

    def test_verification_attempts_increment(self, test_driver_info):
        """Test: Verificar incremento de intentos de verificación"""
        initial_attempts = test_driver_info.verification_attempts
        test_driver_info.verification_attempts += 1
        assert test_driver_info.verification_attempts == initial_attempts + 1

    def test_verification_details_json(self, test_driver_info):
        """Test: Verificar que los detalles de verificación pueden ser JSON"""
        details = {
            "decision": "APPROVED",
            "final_score": 0.85,
            "recommendations": ["Todo correcto"],
            "component_results": {
                "document": {"score": 0.9},
                "selfie": {"score": 0.8},
                "face_comparison": {"similarity_score": 0.85}
            }
        }

        test_driver_info.document_verification_details = details
        assert test_driver_info.document_verification_details == details
        assert test_driver_info.document_verification_details["decision"] == "APPROVED"
        assert test_driver_info.document_verification_details["final_score"] == 0.85


class TestNotificationTemplates:
    """Tests específicos para las plantillas de notificación"""

    def test_verification_approved_template(self):
        """Test: Plantilla de verificación aprobada"""
        template = NotificationTemplates.verification_approved()

        assert template["title"] == "¡Verificación aprobada!"
        assert "Ya puedes comenzar a operar" in template["body"]
        assert template["data"]["type"] == "verification_approved"
        assert template["data"]["action"] == "start_operating"

    def test_verification_rejected_template(self):
        """Test: Plantilla de verificación rechazada"""
        recommendations = ["Problema 1", "Problema 2", "Problema 3"]
        template = NotificationTemplates.verification_rejected(recommendations)

        assert template["title"] == "Verificación rechazada"
        assert "no pudo ser verificada automáticamente" in template["body"]
        assert template["data"]["type"] == "verification_rejected"
        assert template["data"]["action"] == "review_documents"
        assert "recommendations" in template["data"]

    def test_verification_manual_review_template(self):
        """Test: Plantilla de revisión manual"""
        template = NotificationTemplates.verification_manual_review()

        assert template["title"] == "Verificación en revisión"
        assert "está siendo revisada manualmente" in template["body"]
        assert template["data"]["type"] == "verification_manual_review"
        assert template["data"]["action"] == "wait_for_review"

    def test_verification_manual_approved_template(self):
        """Test: Plantilla de aprobación manual"""
        template = NotificationTemplates.verification_manual_approved()

        assert template["title"] == "¡Verificación aprobada!"
        assert "revisada y aprobada por nuestro equipo" in template["body"]
        assert template["data"]["type"] == "verification_manual_approved"
        assert template["data"]["action"] == "start_operating"

    def test_verification_manual_rejected_template(self):
        """Test: Plantilla de rechazo manual"""
        reason = "Documentos ilegibles"
        template = NotificationTemplates.verification_manual_rejected(reason)

        assert template["title"] == "Verificación no aprobada"
        assert "no fue aprobada después de la revisión manual" in template["body"]
        assert reason in template["body"]
        assert template["data"]["type"] == "verification_manual_rejected"
        assert template["data"]["action"] == "contact_support"
        assert template["data"]["reason"] == reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
