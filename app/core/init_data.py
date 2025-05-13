from sqlmodel import Session, select
from datetime import datetime
from app.models.role import Role
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.document_type import DocumentType
from app.models.user import User, UserCreate
from app.models.vehicle_type import VehicleType
from app.core.db import engine
from app.core.config import settings
from app.models.driver import DriverDocumentsInput
from app.services.driver_service import DriverService
from app.models.driver_info import DriverInfoCreate
from app.models.vehicle_info import VehicleInfoCreate


def init_roles():
    roles = [
        Role(id="CLIENT", name="pasajero", route="/client"),
        Role(id="DRIVER", name="conductor", route="/driver")
    ]
    with Session(engine) as session:
        for role in roles:
            exists = session.exec(
                select(Role).where(Role.id == role.id)).first()
            if not exists:
                session.add(role)
        session.commit()


def init_document_types():
    document_types = [
        DocumentType(name="property_card"),
        DocumentType(name="license"),
        DocumentType(name="soat"),
        DocumentType(name="technical_inspections")
    ]
    with Session(engine) as session:
        for doc_type in document_types:
            exists = session.exec(
                select(DocumentType).where(DocumentType.name == doc_type.name)).first()
            if not exists:
                session.add(doc_type)
        session.commit()


def init_test_user():
    with Session(engine) as session:
        # Buscar si ya existe el usuario de prueba
        user = session.exec(select(User).where(
            User.full_name == "prueba_cliente")).first()
        if not user:
            user = User(
                full_name="prueba_cliente",
                country_code="+57",
                phone_number=settings.TEST_CLIENT_PHONE,
                is_verified_phone=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        # Asignar el rol CLIENT si no lo tiene y verificarlo
        client_role = session.exec(
            select(Role).where(Role.id == "CLIENT")).first()
        if client_role and client_role not in user.roles:
            user.roles.append(client_role)
            session.add(user)
            session.commit()

            # Actualizar el estado del rol a verificado
            user_has_role = session.exec(
                select(UserHasRole).where(
                    UserHasRole.id_user == user.id,
                    UserHasRole.id_rol == client_role.id
                )
            ).first()

            if user_has_role:
                user_has_role.is_verified = True
                user_has_role.status = RoleStatus.APPROVED
                user_has_role.verified_at = datetime.utcnow()
                session.add(user_has_role)
                session.commit()

        # Crear datos del documento del conductor
        driver_documents_data = DriverDocumentsInput(
            property_card_front_url="string",
            property_card_back_url="string",
            license_front_url="string",
            license_back_url="string",
            license_expiration_date="2025-05-12",
            soat_url="string",
            soat_expiration_date="2025-05-12",
            vehicle_technical_inspection_url="string",
            vehicle_technical_inspection_expiration_date="2025-05-12"
        )


def init_vehicle_types():
    with Session(engine) as session:
        # Verificar si ya existen tipos de vehículos
        existing_types = session.exec(select(VehicleType)).all()
        if existing_types:
            return

        # Crear tipos de vehículos
        vehicle_types = [
            VehicleType(name="car", capacity=4),
            VehicleType(name="moto", capacity=1)
        ]

        for vehicle_type in vehicle_types:
            session.add(vehicle_type)

        session.commit()


def init_data():
    init_roles()
    init_document_types()
    init_test_user()
    init_vehicle_types()
