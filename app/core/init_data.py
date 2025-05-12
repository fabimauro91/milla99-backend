from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.models.role import Role
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.document_type import DocumentType
from app.models.driver_documents import DriverDocuments, DriverStatus
from app.core.db import engine
from app.core.config import settings


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

def init_test_driver():
    with Session(engine) as session:
        # Buscar si ya existe el conductor de prueba
        driver = session.exec(select(User).where(
            User.full_name == "prueba_conductor")).first()

        if not driver:
            driver = User(
                full_name="prueba_conductor",
                country_code="+57",
                phone_number="3001234567",
                is_verified_phone=True,
                is_active=True
            )
            session.add(driver)
            session.commit()
            session.refresh(driver)

        # Asignar el rol DRIVER si no lo tiene y verificarlo
        driver_role = session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        if driver_role and driver_role not in driver.roles:
            driver.roles.append(driver_role)
            session.add(driver)
            session.commit()

            # Actualizar el estado del rol a verificado
            user_has_role = session.exec(
                select(UserHasRole).where(
                    UserHasRole.id_user == driver.id,
                    UserHasRole.id_rol == driver_role.id
                )
            ).first()

            if user_has_role:
                user_has_role.is_verified = True
                user_has_role.status = RoleStatus.PENDING
                user_has_role.verified_at = datetime.utcnow()
                session.add(user_has_role)
                session.commit()

        return driver

def init_driver_documents():
    with Session(engine) as session:
        # Obtener el conductor de prueba (ahora dentro de la misma sesión)
        driver = session.exec(
            select(User).where(User.full_name == "prueba_conductor")
        ).first()

        if not driver:
            driver = User(
                full_name="prueba_conductor",
                country_code="+57",
                phone_number="3001234567",
                is_verified_phone=True,
                is_active=True
            )
            session.add(driver)
            session.commit()
            session.refresh(driver)

            # Asignar el rol DRIVER
            driver_role = session.exec(
                select(Role).where(Role.id == "DRIVER")
            ).first()
            if driver_role:
                user_has_role = UserHasRole(
                    id_user=driver.id,
                    id_rol=driver_role.id,
                    is_verified=True,
                    status=RoleStatus.PENDING,
                    verified_at=datetime.utcnow()
                )
                session.add(user_has_role)
                session.commit()

        # Obtener los tipos de documentos
        license_type = session.exec(
            select(DocumentType).where(DocumentType.name == "license")
        ).first()
        soat_type = session.exec(
            select(DocumentType).where(DocumentType.name == "soat")
        ).first()
        tech_type = session.exec(
            select(DocumentType).where(DocumentType.name == "technical_inspections")
        ).first()
        card_type = session.exec(
            select(DocumentType).where(DocumentType.name == "property_card")
        ).first()

        # Crear documentos por defecto si no existen
        default_docs = [
            {
                "doc_type": license_type,
                "front_url": "https://example.com/license_front.jpg",
                "back_url": "https://example.com/license_back.jpg",
                "expiration_date": datetime.utcnow() + timedelta(days=65)
            },
            {
                "doc_type": soat_type,
                "front_url": "https://example.com/soat_front.jpg",
                "back_url": None,
                "expiration_date": datetime.utcnow() + timedelta(days=5)
            },
            {
                "doc_type": tech_type,
                "front_url": "https://example.com/tech_front.jpg",
                "back_url": None,
                "expiration_date": datetime.utcnow() + timedelta(days=3)
            },
            {
                "doc_type": card_type,
                "front_url": "https://example.com/card_front.jpg",
                "back_url": "https://example.com/card_front.jpg",
                "expiration_date": datetime.utcnow() + timedelta(days=365)
            }
        ]

        for doc in default_docs:
            if doc["doc_type"]:  # Verificar que el tipo de documento existe
                # Verificar si el documento ya existe
                existing_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.user_id == driver.id,
                        DriverDocuments.document_type_id == doc["doc_type"].id
                    )
                ).first()

                if not existing_doc:
                    new_doc = DriverDocuments(
                        user_id=driver.id,
                        document_type_id=doc["doc_type"].id,
                        document_front_url=doc["front_url"],
                        document_back_url=doc["back_url"],
                        status=DriverStatus.PENDING,
                        expiration_date=doc["expiration_date"]
                    )
                    session.add(new_doc)

        session.commit()

def init_data():
    init_roles()
    init_document_types()
    init_test_user()
    init_driver_documents()