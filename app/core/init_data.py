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
from decimal import Decimal
import shutil
import os
from app.models.vehicle_type_configuration import VehicleTypeConfiguration
from app.services.type_service_service import TypeServiceService
from app.models.type_service import TypeService
from app.models.client_request import ClientRequest, StatusEnum
from app.models.driver_position import DriverPosition
from geoalchemy2.shape import from_shape
from shapely.geometry import Point


def init_roles():
    roles = [
        Role(id="CLIENT", name="pasajero", route="/client"),
        Role(id="DRIVER", name="conductor", route="/driver"),
        Role(id="ADMIN", name="administrador", route="/admin")
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

        # Guardar selfie demo en static/uploads/users/{user.id}/selfie.jpg y asignar url a user.selfie_url
        selfie_dir = os.path.join("static", "uploads", "users", str(user.id))
        os.makedirs(selfie_dir, exist_ok=True)
        selfie_path = os.path.join(selfie_dir, "selfie.jpg")
        shutil.copyfile("img/demo/front foto.jpg", selfie_path)
        user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
        session.add(user)
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

        # Crear tipos de vehículos con sus capacidades
        vehicle_types = [
            VehicleType(
                name="Car",
                description="Four-wheeled vehicle for passenger transportation",
                capacity=4
            ),
            VehicleType(
                name="Motorcycle",
                description="Two-wheeled vehicle for passenger transportation",
                capacity=1
            )
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
                # Asociar al primer VehicleType (car)
                vehicle_type_id=vehicle_types[0].id
            ),
            VehicleTypeConfiguration(
                km_value=800.0,
                min_value=100.0,
                tarifa_value=3000.0,
                weight_value=350.0,
                # Asociar al segundo VehicleType (moto)
                vehicle_type_id=vehicle_types[1].id
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
            driver_info = DriverInfo(
                user_id=user.id,
                first_name="John",
                last_name="Doe",
                birth_date=date(1990, 1, 1),
                email="john@example.com"
            )
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)

        # Guardar selfie demo en static/uploads/users/{user.id}/selfie.jpg y asignar url a user.selfie_url
        selfie_dir = os.path.join("static", "uploads", "users", str(user.id))
        os.makedirs(selfie_dir, exist_ok=True)
        selfie_path = os.path.join(selfie_dir, "selfie.jpg")
        shutil.copyfile("img/demo/front foto.jpg", selfie_path)
        user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
        session.add(user)
        session.commit()

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


def init_additional_clients():
    """Inicializa 4 clientes adicionales con datos de prueba"""
    with Session(engine) as session:
        # Lista de clientes a crear
        clients_data = [
            {
                "full_name": "María García",
                "phone_number": "3001111111",
                "selfie_url": None
            },
            {
                "full_name": "Juan Pérez",
                "phone_number": "3002222222",
                "selfie_url": None
            },
            {
                "full_name": "Ana Martínez",
                "phone_number": "3003333333",
                "selfie_url": None
            },
            {
                "full_name": "Carlos Rodríguez",
                "phone_number": "3004444444",
                "selfie_url": None
            }
        ]

        # Obtener el rol CLIENT
        client_role = session.exec(
            select(Role).where(Role.id == "CLIENT")).first()

        for client_data in clients_data:
            # Verificar si el cliente ya existe
            existing_user = session.exec(select(User).where(
                User.phone_number == client_data["phone_number"]
            )).first()

            if not existing_user:
                # Crear nuevo usuario
                user = User(
                    full_name=client_data["full_name"],
                    country_code="+57",
                    phone_number=client_data["phone_number"],
                    is_verified_phone=True,
                    is_active=True
                )
                session.add(user)
                session.commit()
                session.refresh(user)

                # Asignar rol CLIENT
                if client_role and client_role not in user.roles:
                    user.roles.append(client_role)
                    session.add(user)
                    session.commit()

                    # Actualizar estado del rol
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

                # Guardar selfie demo
                selfie_dir = os.path.join(
                    "static", "uploads", "users", str(user.id))
                os.makedirs(selfie_dir, exist_ok=True)
                selfie_path = os.path.join(selfie_dir, "selfie.jpg")
                shutil.copyfile("img/demo/front foto.jpg", selfie_path)
                user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
                session.add(user)
                session.commit()


def init_additional_drivers():
    """Inicializa 4 conductores adicionales (2 con carro y 2 con moto)"""
    with Session(engine) as session:
        # Datos de los conductores
        drivers_data = [
            # Conductores con carro
            {
                "user": {
                    "full_name": "Roberto Sánchez",
                    "phone_number": "3005555555"
                },
                "driver_info": {
                    "first_name": "Roberto",
                    "last_name": "Sánchez",
                    "birth_date": date(1985, 5, 15),
                    "email": "roberto.sanchez@example.com"
                },
                "vehicle_info": {
                    "brand": "Chevrolet",
                    "model": "Onix",
                    "model_year": 2023,
                    "color": "Blanco",
                    "plate": "ABC123"
                }
            },
            {
                "user": {
                    "full_name": "Laura Torres",
                    "phone_number": "3006666666"
                },
                "driver_info": {
                    "first_name": "Laura",
                    "last_name": "Torres",
                    "birth_date": date(1990, 8, 20),
                    "email": "laura.torres@example.com"
                },
                "vehicle_info": {
                    "brand": "Renault",
                    "model": "Kwid",
                    "model_year": 2022,
                    "color": "Rojo",
                    "plate": "DEF456"
                }
            },
            # Conductores con moto
            {
                "user": {
                    "full_name": "Pedro Gómez",
                    "phone_number": "3007777777"
                },
                "driver_info": {
                    "first_name": "Pedro",
                    "last_name": "Gómez",
                    "birth_date": date(1988, 3, 10),
                    "email": "pedro.gomez@example.com"
                },
                "vehicle_info": {
                    "brand": "Yamaha",
                    "model": "FZ 2.0",
                    "model_year": 2023,
                    "color": "Negro",
                    "plate": "GHI789"
                }
            },
            {
                "user": {
                    "full_name": "Sofía Ramírez",
                    "phone_number": "3008888888"
                },
                "driver_info": {
                    "first_name": "Sofía",
                    "last_name": "Ramírez",
                    "birth_date": date(1992, 11, 25),
                    "email": "sofia.ramirez@example.com"
                },
                "vehicle_info": {
                    "brand": "Honda",
                    "model": "CB 190R",
                    "model_year": 2022,
                    "color": "Azul",
                    "plate": "JKL012"
                }
            }
        ]

        # Obtener roles y tipos necesarios
        driver_role = session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        car_type = session.exec(select(VehicleType).where(
            VehicleType.name == "Car")).first()
        moto_type = session.exec(select(VehicleType).where(
            VehicleType.name == "Motorcycle")).first()

        # Obtener tipos de documentos
        license_type = session.exec(select(DocumentType).where(
            DocumentType.name == "license")).first()
        soat_type = session.exec(select(DocumentType).where(
            DocumentType.name == "soat")).first()
        tech_type = session.exec(select(DocumentType).where(
            DocumentType.name == "technical_inspections")).first()
        card_type = session.exec(select(DocumentType).where(
            DocumentType.name == "property_card")).first()

        for i, driver_data in enumerate(drivers_data):
            # Verificar si el conductor ya existe
            existing_user = session.exec(select(User).where(
                User.phone_number == driver_data["user"]["phone_number"]
            )).first()

            if not existing_user:
                # Crear usuario
                user = User(
                    full_name=driver_data["user"]["full_name"],
                    country_code="+57",
                    phone_number=driver_data["user"]["phone_number"],
                    is_verified_phone=True,
                    is_active=True
                )
                session.add(user)
                session.commit()
                session.refresh(user)

                # Asignar rol DRIVER
                if driver_role and driver_role not in user.roles:
                    user.roles.append(driver_role)
                    session.add(user)
                    session.commit()

                    # Actualizar estado del rol a APPROVED
                    user_has_role = session.exec(
                        select(UserHasRole).where(
                            UserHasRole.id_user == user.id,
                            UserHasRole.id_rol == driver_role.id
                        )
                    ).first()

                    if user_has_role:
                        user_has_role.is_verified = True
                        user_has_role.status = RoleStatus.APPROVED
                        user_has_role.verified_at = datetime.utcnow()
                        session.add(user_has_role)
                        session.commit()

                # Guardar selfie
                selfie_dir = os.path.join(
                    "static", "uploads", "users", str(user.id))
                os.makedirs(selfie_dir, exist_ok=True)
                selfie_path = os.path.join(selfie_dir, "selfie.jpg")
                shutil.copyfile("img/demo/front foto.jpg", selfie_path)
                user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
                session.add(user)
                session.commit()

                # Crear DriverInfo
                driver_info = DriverInfo(
                    user_id=user.id,
                    first_name=driver_data["driver_info"]["first_name"],
                    last_name=driver_data["driver_info"]["last_name"],
                    birth_date=driver_data["driver_info"]["birth_date"],
                    email=driver_data["driver_info"]["email"],
                    selfie_url=user.selfie_url
                )
                session.add(driver_info)
                session.commit()
                session.refresh(driver_info)

                # Crear VehicleInfo
                vehicle_type_id = car_type.id if i < 2 else moto_type.id
                vehicle_info = VehicleInfo(
                    brand=driver_data["vehicle_info"]["brand"],
                    model=driver_data["vehicle_info"]["model"],
                    model_year=driver_data["vehicle_info"]["model_year"],
                    color=driver_data["vehicle_info"]["color"],
                    plate=driver_data["vehicle_info"]["plate"],
                    vehicle_type_id=vehicle_type_id,
                    driver_info_id=driver_info.id
                )
                session.add(vehicle_info)
                session.commit()
                session.refresh(vehicle_info)

                # Crear documentos del conductor
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
                        new_doc = DriverDocuments(
                            document_type_id=doc["doc_type"].id,
                            document_front_url=doc["front_url"],
                            document_back_url=doc["back_url"],
                            status=DriverStatus.APPROVED,  # Establecer como APPROVED
                            expiration_date=doc["expiration_date"],
                            driver_info_id=driver_info.id,
                            vehicle_info_id=vehicle_info.id
                        )
                        session.add(new_doc)

                        # Copiar archivos demo
                        if doc["front_url"]:
                            dest_path = os.path.join(
                                "static/uploads", doc["front_url"].replace(f"{settings.STATIC_URL_PREFIX}/", ""))
                            os.makedirs(os.path.dirname(
                                dest_path), exist_ok=True)
                            shutil.copyfile(
                                "img/demo/front foto.jpg", dest_path)
                        if doc["back_url"]:
                            dest_path = os.path.join(
                                "static/uploads", doc["back_url"].replace(f"{settings.STATIC_URL_PREFIX}/", ""))
                            os.makedirs(os.path.dirname(
                                dest_path), exist_ok=True)
                            shutil.copyfile(
                                "img/demo/back foto.jpg", dest_path)

                session.commit()


def init_client_requests_and_driver_positions():
    """Inicializa solicitudes de viaje y posiciones de conductores"""
    # Primero crear las solicitudes de clientes
    with Session(engine) as session:
        try:
            # Importar modelos necesarios
            from app.models.type_service import TypeService
            from app.models.client_request import ClientRequest, StatusEnum
            from app.models.driver_position import DriverPosition
            from geoalchemy2.shape import from_shape
            from shapely.geometry import Point

            # Coordenadas de prueba en Bogotá
            TEST_COORDINATES = {
                # Conductores
                "drivers": {
                    "roberto_sanchez": {  # Conductor de carro
                        "lat": 4.708822,
                        "lng": -74.076542
                    },
                    "laura_torres": {  # Conductor de carro
                        "lat": 4.712345,
                        "lng": -74.078901
                    },
                    "pedro_gomez": {  # Conductor de moto
                        "lat": 4.715678,
                        "lng": -74.081234
                    },
                    "sofia_ramirez": {  # Conductor de moto
                        "lat": 4.719012,
                        "lng": -74.083567
                    }
                },
                # Puntos de recogida
                "pickup_points": {
                    "suba": {
                        "lat": 4.718136,
                        "lng": -74.073170,
                        "description": "Suba Bogotá"
                    },
                    "engativa": {
                        "lat": 4.702468,
                        "lng": -74.109776,
                        "description": "Santa Rosita Engativa"
                    },
                    "chapinero": {
                        "lat": 4.648270,
                        "lng": -74.061890,
                        "description": "Chapinero Centro"
                    },
                    "kennedy": {
                        "lat": 4.609710,
                        "lng": -74.151750,
                        "description": "Kennedy Central"
                    }
                },
                # Destinos
                "destinations": {
                    "centro": {
                        "lat": 4.598100,
                        "lng": -74.076100,
                        "description": "Centro Internacional"
                    },
                    "norte": {
                        "lat": 4.798100,
                        "lng": -74.046100,
                        "description": "Centro Comercial Andino"
                    },
                    "occidente": {
                        "lat": 4.698100,
                        "lng": -74.126100,
                        "description": "Centro Comercial Metrópolis"
                    },
                    "sur": {
                        "lat": 4.558100,
                        "lng": -74.146100,
                        "description": "Portal Sur"
                    }
                }
            }

            # Obtener IDs de tipos de servicio
            car_service = session.exec(
                select(TypeService)
                .join(VehicleType)
                .where(VehicleType.name == "Car")
            ).first()
            moto_service = session.exec(
                select(TypeService)
                .join(VehicleType)
                .where(VehicleType.name == "Motorcycle")
            ).first()

            if not car_service or not moto_service:
                raise Exception("No se encontraron los tipos de servicio")

            # Obtener usuarios (clientes)
            clients = {}
            for phone in ["3001111111", "3002222222", "3003333333", "3004444444"]:
                client = session.exec(select(User).where(
                    User.phone_number == phone)).first()
                if not client:
                    continue
                clients[phone] = client

            if not clients:
                raise Exception(
                    "No se encontraron clientes para crear solicitudes")

            # Crear solicitudes de viaje solo para los clientes encontrados
            requests_data = []
            if "3001111111" in clients:  # María García (carro)
                requests_data.extend([
                    {"client": clients["3001111111"], "type": car_service.id,
                        "pickup": "suba", "destination": "centro"},
                    {"client": clients["3001111111"], "type": car_service.id,
                        "pickup": "engativa", "destination": "norte"}
                ])
            if "3002222222" in clients:  # Juan Pérez (carro)
                requests_data.extend([
                    {"client": clients["3002222222"], "type": car_service.id,
                        "pickup": "chapinero", "destination": "occidente"},
                    {"client": clients["3002222222"], "type": car_service.id,
                        "pickup": "kennedy", "destination": "sur"}
                ])
            if "3003333333" in clients:  # Ana Martínez (moto)
                requests_data.extend([
                    {"client": clients["3003333333"], "type": moto_service.id,
                        "pickup": "suba", "destination": "norte"},
                    {"client": clients["3003333333"], "type": moto_service.id,
                        "pickup": "engativa", "destination": "centro"}
                ])
            if "3004444444" in clients:  # Carlos Rodríguez (moto)
                requests_data.extend([
                    {"client": clients["3004444444"], "type": moto_service.id,
                        "pickup": "chapinero", "destination": "sur"},
                    {"client": clients["3004444444"], "type": moto_service.id,
                        "pickup": "kennedy", "destination": "occidente"}
                ])

            # Crear las solicitudes
            created_requests = []  # Lista para almacenar las solicitudes creadas
            for req_data in requests_data:
                if not req_data["client"] or not req_data["client"].id:
                    continue

                pickup = TEST_COORDINATES["pickup_points"][req_data["pickup"]]
                dest = TEST_COORDINATES["destinations"][req_data["destination"]]

                try:
                    id_client = req_data["client"].id

                    # Crear solicitud con validación explícita
                    request = ClientRequest(
                        id_client=id_client,
                        type_service_id=req_data["type"],
                        fare_offered=20000,
                        pickup_description=pickup["description"],
                        destination_description=dest["description"],
                        pickup_position=from_shape(
                            Point(pickup["lng"], pickup["lat"]), srid=4326),
                        destination_position=from_shape(
                            Point(dest["lng"], dest["lat"]), srid=4326),
                        status=StatusEnum.CREATED
                    )

                    # Validar que el id_client se mantuvo
                    if request.id_client != id_client:
                        continue

                    session.add(request)
                    created_requests.append(request)
                except Exception as e:
                    continue

            # Commit de las solicitudes
            session.commit()
        except Exception as e:
            session.rollback()
            raise

    # Luego actualizar las posiciones de los conductores en una transacción separada
    with Session(engine) as session:
        try:
            # Obtener conductores
            drivers = {}
            for phone in ["3005555555", "3006666666", "3007777777", "3008888888"]:
                driver = session.exec(select(User).where(
                    User.phone_number == phone)).first()
                if not driver:
                    continue
                drivers[phone] = driver

            if not drivers:
                raise Exception(
                    "No se encontraron conductores para actualizar posiciones")

            # Actualizar posiciones de conductores
            for phone, driver in drivers.items():
                if not driver or not driver.id:
                    continue

                driver_coords = None
                if phone == "3005555555":
                    driver_coords = TEST_COORDINATES["drivers"]["roberto_sanchez"]
                elif phone == "3006666666":
                    driver_coords = TEST_COORDINATES["drivers"]["laura_torres"]
                elif phone == "3007777777":
                    driver_coords = TEST_COORDINATES["drivers"]["pedro_gomez"]
                elif phone == "3008888888":
                    driver_coords = TEST_COORDINATES["drivers"]["sofia_ramirez"]

                if driver_coords:
                    try:
                        with session.no_autoflush:
                            position = DriverPosition(
                                id_driver=driver.id,
                                position=from_shape(
                                    Point(driver_coords["lng"], driver_coords["lat"]), srid=4326)
                            )
                            session.merge(position)
                    except Exception as e:
                        continue

            # Commit de las posiciones
            session.commit()
        except Exception as e:
            session.rollback()
            raise


def init_data():
    """Inicializa los datos por defecto de la aplicación"""
    session = Session(engine)

    try:
        # Primero inicializar roles y tipos de documento
        init_roles()
        init_document_types()

        # Luego inicializar tipos de vehículo
        vehicle_types = init_vehicle_types(engine)
        if not vehicle_types:
            # Si ya existen, obténlos de la base de datos
            with Session(engine) as session:
                vehicle_types = session.exec(select(VehicleType)).all()

        # Después inicializar tipos de servicio (que dependen de los tipos de vehículo)
        type_service_service = TypeServiceService(session)
        type_service_service.init_default_types()

        # Inicializar usuarios de prueba
        init_test_user()
        init_additional_clients()  # Agregar 4 clientes adicionales
        init_driver_documents()
        init_time_distance_values(engine, vehicle_types)
        init_demo_driver()
        init_additional_drivers()  # Agregar 4 conductores adicionales
        # Agregar solicitudes y posiciones de conductores
        init_client_requests_and_driver_positions()

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
