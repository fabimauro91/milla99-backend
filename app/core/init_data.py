from sqlmodel import Session, select
from datetime import datetime, timedelta, date
from datetime import datetime
from app.models.role import Role
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.document_type import DocumentType
from app.models.driver_documents import DriverDocuments, DriverStatus
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.document_type import DocumentType
from app.models.user import User, UserCreate
from app.models.vehicle_type import VehicleType
from app.models.driver_info import DriverInfo
from app.core.db import engine
from app.core.config import settings
from app.models.driver import DriverDocumentsInput
from app.services.driver_service import DriverService
from app.models.driver_info import DriverInfoCreate
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate
from app.utils.uploads import uploader
import shutil
import os
from app.models.vehicle_type_configuration import VehicleTypeConfiguration


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


def init_vehicle_types(engine):
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
        session.refresh(vehicle_types[0])  # Refrescar para obtener el ID
        session.refresh(vehicle_types[1])  # Refrescar para obtener el ID
        return vehicle_types  # Retornar los tipos de vehículos creados


def init_time_distance_values(engine, vehicle_types):
    with Session(engine) as session:
        # Verificar si ya existen registros
        existing_values = session.exec(select(VehicleTypeConfiguration)).all()
        if existing_values:
            return

        # Crear valores iniciales y asociarlos a VehicleType
        time_distance_values = [
            VehicleTypeConfiguration(
                km_value=1200.0,
                min_value=150.0,
                tarifa_value=6000.0,
                weight_value=350.5,
                vehicle_type_id=vehicle_types[0].id  # Asociar al primer VehicleType (car)
            ),
            VehicleTypeConfiguration(
                km_value=800.0,
                min_value=100.0,
                tarifa_value=3000.0,
                weight_value=350.0,
                vehicle_type_id=vehicle_types[1].id  # Asociar al segundo VehicleType (moto)
            )
        ]

        for value in time_distance_values:
            session.add(value)

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
                phone_number="3148780278",
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
                    status=RoleStatus.APPROVED,
                    verified_at=datetime.utcnow()
                )
                session.add(user_has_role)
                session.commit()
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

        # Obtener los tipos de documentos
        license_type = session.exec(
            select(DocumentType).where(DocumentType.name == "license")
        ).first()
        soat_type = session.exec(
            select(DocumentType).where(DocumentType.name == "soat")
        ).first()
        tech_type = session.exec(
            select(DocumentType).where(
                DocumentType.name == "technical_inspections")
        ).first()
        card_type = session.exec(
            select(DocumentType).where(DocumentType.name == "property_card")
        ).first()

        if driver:
            # Verificar si ya existe un DriverInfo para este usuario
            driver_info = session.exec(
                select(DriverInfo).where(DriverInfo.user_id == driver.id)
            ).first()

            if not driver_info:
                # Crear el DriverInfo
                driver_info = DriverInfo(
                    user_id=driver.id,
                    first_name="prueva",
                    last_name="conductor",
                    birth_date=date(1990, 1, 1),  # Fecha de ejemplo
                    email="conductor.prueba@example.com",
                    selfie_url="https://example.com/selfie.jpg"
                )
                session.add(driver_info)
                session.commit()
                session.refresh(driver_info)

            # Crear VehicleInfo para el driver de prueba si no existe
            vehicle_info = session.exec(
                select(VehicleInfo).where(
                    VehicleInfo.driver_info_id == driver_info.id)
            ).first()

            if not vehicle_info:
                vehicle_type = session.exec(select(VehicleType).where(
                    VehicleType.name == "car")).first()
                vehicle_info = VehicleInfo(
                    brand="Tesla",
                    model="Tracker",
                    model_year=2024,
                    color="Azul",
                    plate="XYZ987",
                    vehicle_type_id=vehicle_type.id if vehicle_type else 1,
                    driver_info_id=driver_info.id
                )
                session.add(vehicle_info)
                session.commit()
                session.refresh(vehicle_info)

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
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == doc["doc_type"].id
                    )
                ).first()

                if not existing_doc:
                    new_doc = DriverDocuments(
                        document_type_id=doc["doc_type"].id,
                        document_front_url=doc["front_url"],
                        document_back_url=doc["back_url"],
                        status=DriverStatus.PENDING,
                        expiration_date=doc["expiration_date"],
                        driver_info_id=driver_info.id
                    )
                    session.add(new_doc)

        session.commit()


def init_demo_driver():
    with Session(engine) as session:
        # 1. Crear o buscar usuario demo
        user = session.exec(select(User).where(
            User.full_name == "demo_driver")).first()
        if not user:
            user = User(
                full_name="demo_driver",
                country_code="+57",
                phone_number="3009999999",
                is_verified_phone=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        # 2. Asignar el rol DRIVER si no lo tiene
        driver_role = session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        if driver_role and driver_role not in user.roles:
            user.roles.append(driver_role)
            session.add(user)
            session.commit()
            session.refresh(user)

        # 3. Crear o buscar DriverInfo
        driver_info = session.exec(select(DriverInfo).where(
            DriverInfo.user_id == user.id)).first()
        if not driver_info:
            selfie_rel = f"drivers/{user.id}/selfie/demo_selfie.jpg"
            selfie_url = uploader.get_file_url(selfie_rel)
            driver_info = DriverInfo(
                user_id=user.id,
                first_name="John",
                last_name="Doe",
                birth_date=date(1990, 1, 1),
                email="john@example.com",
                selfie_url=selfie_url
            )
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)
            # Copiar selfie demo
            selfie_dest = os.path.join("static/uploads", selfie_rel)
            os.makedirs(os.path.dirname(selfie_dest), exist_ok=True)
            shutil.copyfile("img/demo/front foto.jpg", selfie_dest)

        # 4. Crear o buscar VehicleInfo
        vehicle_type = session.exec(select(VehicleType).where(
            VehicleType.name == "car")).first()
        vehicle_info = session.exec(select(VehicleInfo).where(
            VehicleInfo.driver_info_id == driver_info.id)).first()
        if not vehicle_info:
            vehicle_info = VehicleInfo(
                brand="Toyota",
                model="Corolla",
                model_year=2004,
                color="Red",
                plate="ABC123",
                vehicle_type_id=vehicle_type.id if vehicle_type else 1,
                driver_info_id=driver_info.id
            )
            session.add(vehicle_info)
            session.commit()
            session.refresh(vehicle_info)

        # 5. Obtener tipos de documentos
        license_type = session.exec(select(DocumentType).where(
            DocumentType.name == "license")).first()
        soat_type = session.exec(select(DocumentType).where(
            DocumentType.name == "soat")).first()
        tech_type = session.exec(select(DocumentType).where(
            DocumentType.name == "technical_inspections")).first()
        card_type = session.exec(select(DocumentType).where(
            DocumentType.name == "property_card")).first()

        # 6. Crear documentos demo con rutas reales y URLs completas
        demo_docs = [
            {
                "doc_type": license_type,
                "front_url": uploader.get_file_url(f"drivers/{driver_info.id}/license/demo_license_front.jpg"),
                "back_url": uploader.get_file_url(f"drivers/{driver_info.id}/license/demo_license_back.jpg"),
                "expiration_date": date(2025, 1, 1)
            },
            {
                "doc_type": soat_type,
                "front_url": uploader.get_file_url(f"drivers/{driver_info.id}/soat/demo_soat_front.jpg"),
                "back_url": None,
                "expiration_date": date(2024, 12, 31)
            },
            {
                "doc_type": tech_type,
                "front_url": uploader.get_file_url(f"drivers/{driver_info.id}/technical_inspections/demo_tech_front.jpg"),
                "back_url": None,
                "expiration_date": date(2024, 12, 31)
            },
            {
                "doc_type": card_type,
                "front_url": uploader.get_file_url(f"drivers/{driver_info.id}/property_card/demo_card_front.jpg"),
                "back_url": uploader.get_file_url(f"drivers/{driver_info.id}/property_card/demo_card_back.jpg"),
                "expiration_date": date(2025, 12, 31)
            }
        ]

        for doc in demo_docs:
            if doc["doc_type"]:
                existing_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == doc["doc_type"].id
                    )
                ).first()
                if not existing_doc:
                    new_doc = DriverDocuments(
                        document_type_id=doc["doc_type"].id,
                        document_front_url=doc["front_url"],
                        document_back_url=doc["back_url"],
                        status=DriverStatus.PENDING,
                        expiration_date=doc["expiration_date"],
                        driver_info_id=driver_info.id,
                        vehicle_info_id=vehicle_info.id
                    )
                    session.add(new_doc)
                    # Copiar archivo demo si no existe
                    if doc["front_url"]:
                        dest_path = os.path.join(
                            "static/uploads", doc["front_url"].replace(f"{settings.STATIC_URL_PREFIX}/", ""))
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copyfile("img/demo/front foto.jpg", dest_path)
                    if doc["back_url"]:
                        dest_path = os.path.join(
                            "static/uploads", doc["back_url"].replace(f"{settings.STATIC_URL_PREFIX}/", ""))
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copyfile("img/demo/back foto.jpg", dest_path)
        session.commit()

def init_data():
    init_roles()
    init_document_types()
    init_test_user()
    init_driver_documents()
    vehicle_types = init_vehicle_types(engine)
    if not vehicle_types:
        # Si ya existen, obténlos de la base de datos
        with Session(engine) as session:
            vehicle_types = session.exec(select(VehicleType)).all()
    init_time_distance_values(engine, vehicle_types)
    init_demo_driver()