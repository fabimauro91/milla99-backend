from sqlmodel import Session, select
from datetime import datetime, timedelta, date
from app.models.role import Role
from app.models.transaction import Transaction, TransactionType
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.document_type import DocumentType
from app.models.driver_documents import DriverDocuments, DriverStatus
from app.models.user import User
from app.models.vehicle_type import VehicleType
from app.models.driver_info import DriverInfo
from app.core.db import engine
from app.core.config import settings
from app.models.verify_mount import VerifyMount
from app.models.vehicle_info import VehicleInfo
from app.models.referral_chain import Referral
from app.models.project_settings import ProjectSettings
from app.utils.uploads import uploader
from decimal import Decimal
import shutil
import os
from app.models.config_service_value import ConfigServiceValue
from app.services.type_service_service import TypeServiceService
from app.models.type_service import TypeService
from app.models.client_request import ClientRequest, StatusEnum
from app.models.driver_position import DriverPosition
from app.models.driver_trip_offer import DriverTripOffer
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from uuid import UUID
from app.models.administrador import Administrador
from passlib.hash import bcrypt
from app.models.payment_method import PaymentMethod
import random


def uuid_prueba(num: int) -> UUID:
    """Genera un UUID de prueba con el patrón 00000000-0000-0000-0000-XXXXXXXXXXXX, donde X es el número con padding a 12 dígitos."""
    return UUID(f"00000000-0000-0000-0000-{num:012d}")


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


def init_vehicle_types(engine):
    with Session(engine) as session:
        existing_types = session.exec(select(VehicleType)).all()
        if existing_types:
            return existing_types

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
        for vt in vehicle_types:
            session.refresh(vt)
        return vehicle_types


def init_time_distance_values(engine):
    with Session(engine) as session:
        existing_values = session.exec(select(ConfigServiceValue)).all()
        if existing_values:
            return

        time_distance_values = [
            ConfigServiceValue(
                km_value=1200.0,
                min_value=150.0,
                tarifa_value=6000.0,
                weight_value=350.5,
                service_type_id=1,
            ),
            ConfigServiceValue(
                km_value=800.0,
                min_value=100.0,
                tarifa_value=3000.0,
                weight_value=350.0,
                service_type_id=2,
            )
        ]

        for value in time_distance_values:
            session.add(value)
        session.commit()


def init_project_settings():
    with Session(engine) as session:
        existing_settings = session.exec(select(ProjectSettings)).first()
        if existing_settings:
            return

        project_setting = ProjectSettings(
            driver_dist="2",
            referral_1="0.02",
            referral_2="0.0125",
            referral_3="0.0075",
            referral_4="0.005",
            referral_5="0.005",
            driver_saving="0.01",
            company="0.04",
            bonus="20000",
            amount="50000",
            created_at=datetime(2025, 5, 20, 15, 35, 26),
            updated_at=datetime(2025, 5, 20, 15, 35, 26)
        )
        session.add(project_setting)
        session.commit()


def init_payment_methods(session: Session):
    """Inicializa los métodos de pago básicos."""
    payment_methods = [
        {"id": 1, "name": "cash"},
        {"id": 2, "name": "nequi"},
        {"id": 3, "name": "daviplata"}
    ]

    for pm in payment_methods:
        existing = session.exec(select(PaymentMethod).where(
            PaymentMethod.id == pm["id"])).first()
        if not existing:
            payment_method = PaymentMethod(**pm)
            session.add(payment_method)
    session.commit()


def create_admin(session: Session):
    admin_email = "admin"
    admin_password = "admin"
    admin_role = 1
    hashed_password = bcrypt.hash(admin_password)
    admin = session.exec(
        select(Administrador).where(Administrador.email == admin_email)
    ).first()
    if not admin:
        admin = Administrador(
            email=admin_email, password=hashed_password, role=admin_role)
        session.add(admin)
        session.commit()


# ============================================================================
# NUEVAS FUNCIONES REORGANIZADAS
# ============================================================================

def create_all_users(session: Session):
    """1. Crear todos los usuarios (clientes y conductores)"""
    
    # Datos de clientes
    clients_data = [
        {"full_name": "María García", "phone_number": "3001111111"},
        {"full_name": "Juan Pérez", "phone_number": "3002222222"},
        {"full_name": "Ana Martínez", "phone_number": "3003333333"},
        {"full_name": "Carlos Rodríguez", "phone_number": "3004444444"},
        {"full_name": "Jhonatan Restrepo", "phone_number": "3004442444"},
        {"full_name": "Maricela Muños", "phone_number": "3004444445"},
        {"full_name": "Daniel Carrascal", "phone_number": "3004444446"},
        {"full_name": "Carlos Valderrama", "phone_number": "3004444447"},
        {"full_name": "Carmenza Coyazos", "phone_number": "3004444448"},
        {"full_name": "juan hoyos", "phone_number": "3009644448"},
        {"full_name": "Marcela Jimenez", "phone_number": "3004444449"},
        {"full_name": "Paola Roa", "phone_number": "3004994449"},
        {"full_name": "Jason Avarez", "phone_number": "3004884450"},
        {"full_name": "Pedro Fernandez", "phone_number": "3004444450"},
        {"full_name": "Maritza Rodrigez", "phone_number": "3004444451"},
        {"full_name": "Estephany Pelaez", "phone_number": "3004444452"},
        {"full_name": "Angela ceballos", "phone_number": "3334444452"},
        {"full_name": "Diego Mojica", "phone_number": "3004444453"},
        {"full_name": "Diana Leane", "phone_number": "3004444454"},
        {"full_name": "Taliana Vega", "phone_number": "3004444455"},
        {"full_name": "Paulina Vargas", "phone_number": "3004444456"},
        {"full_name": "Angelina Fernandez", "phone_number": "3004444457"},
        {"full_name": "Cecilia Castrillon", "phone_number": "3004444458"},
        {"full_name": "Paulo Coelo", "phone_number": "3004444459"},
        {"full_name": "Gabriel Garcia", "phone_number": "3004444460"}
    ]

    # Datos de conductores
    drivers_data = [
        {"full_name": "demo_driver", "phone_number": "3009999999"},
        {"full_name": "prueba_conductor", "phone_number": "3148780278"},
        {"full_name": "Roberto Sánchez", "phone_number": "3005555555"},
        {"full_name": "Laura Torres", "phone_number": "3006666666"},
        {"full_name": "Pedro Gómez", "phone_number": "3007777777"},
        {"full_name": "Sofía Ramírez", "phone_number": "3008888888"}
    ]

    # Obtener roles
    client_role = session.exec(select(Role).where(Role.id == "CLIENT")).first()
    driver_role = session.exec(select(Role).where(Role.id == "DRIVER")).first()

    clients = []
    drivers = []

    # Crear clientes
    for client_data in clients_data:
        existing_user = session.exec(select(User).where(
            User.phone_number == client_data["phone_number"]
        )).first()

        if not existing_user:
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
            if client_role:
                user_has_role = UserHasRole(
                    id_user=user.id,
                    id_rol=client_role.id,
                    is_verified=True,
                    status=RoleStatus.APPROVED,
                    verified_at=datetime.utcnow()
                )
                session.add(user_has_role)

            # Crear selfie
            selfie_dir = os.path.join("static", "uploads", "users", str(user.id))
            os.makedirs(selfie_dir, exist_ok=True)
            selfie_path = os.path.join(selfie_dir, "selfie.jpg")
            shutil.copyfile("img/demo/front foto.jpg", selfie_path)
            user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
            session.add(user)

            clients.append(user)

    # Crear conductores (solo usuarios, sin documentos aún)
    for driver_data in drivers_data:
        existing_user = session.exec(select(User).where(
            User.phone_number == driver_data["phone_number"]
        )).first()

        if not existing_user:
            user = User(
                full_name=driver_data["full_name"],
                country_code="+57",
                phone_number=driver_data["phone_number"],
                is_verified_phone=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Asignar rol DRIVER
            if driver_role:
                user_has_role = UserHasRole(
                    id_user=user.id,
                    id_rol=driver_role.id,
                    is_verified=True,
                    status=RoleStatus.APPROVED,
                    verified_at=datetime.utcnow()
                )
                session.add(user_has_role)

            # Crear selfie
            selfie_dir = os.path.join("static", "uploads", "users", str(user.id))
            os.makedirs(selfie_dir, exist_ok=True)
            selfie_path = os.path.join(selfie_dir, "selfie.jpg")
            shutil.copyfile("img/demo/front foto.jpg", selfie_path)
            user.selfie_url = f"{settings.STATIC_URL_PREFIX}/users/{user.id}/selfie.jpg"
            session.add(user)

            drivers.append(user)

    session.commit()
    print(f"✅ Creados {len(clients)} clientes y {len(drivers)} conductores")
    return {'clients': clients, 'drivers': drivers}


def create_all_drivers(session: Session, users):
    """2. Crear y definir todos los drivers con documentos, transacciones y monto"""
    
    drivers = users['drivers']
    
    # Configuración de vehículos por conductor
    driver_configs = [
        # demo_driver - Carro
        {
            "phone": "3009999999",
            "driver_info": {"first_name": "John", "last_name": "Doe", "birth_date": date(1990, 1, 1), "email": "john@example.com"},
            "vehicle_info": {"brand": "Toyota", "model": "Corolla", "model_year": 2004, "color": "Red", "plate": "ABC123", "vehicle_type": "Car"}
        },
        # prueba_conductor - Carro
        {
            "phone": "3148780278",
            "driver_info": {"first_name": "prueva", "last_name": "conductor", "birth_date": date(1990, 1, 1), "email": "conductor.prueba@example.com"},
            "vehicle_info": {"brand": "Tesla", "model": "Tracker", "model_year": 2024, "color": "Azul", "plate": "XYZ987", "vehicle_type": "Car"}
        },
        # Roberto Sánchez - Carro
        {
            "phone": "3005555555",
            "driver_info": {"first_name": "Roberto", "last_name": "Sánchez", "birth_date": date(1985, 5, 15), "email": "roberto.sanchez@example.com"},
            "vehicle_info": {"brand": "Chevrolet", "model": "Onix", "model_year": 2023, "color": "Blanco", "plate": "ROB123", "vehicle_type": "Car"}
        },
        # Laura Torres - Carro
        {
            "phone": "3006666666",
            "driver_info": {"first_name": "Laura", "last_name": "Torres", "birth_date": date(1990, 8, 20), "email": "laura.torres@example.com"},
            "vehicle_info": {"brand": "Renault", "model": "Kwid", "model_year": 2022, "color": "Rojo", "plate": "LAU456", "vehicle_type": "Car"}
        },
        # Pedro Gómez - Moto
        {
            "phone": "3007777777",
            "driver_info": {"first_name": "Pedro", "last_name": "Gómez", "birth_date": date(1988, 3, 10), "email": "pedro.gomez@example.com"},
            "vehicle_info": {"brand": "Yamaha", "model": "FZ 2.0", "model_year": 2023, "color": "Negro", "plate": "PED789", "vehicle_type": "Motorcycle"}
        },
        # Sofía Ramírez - Moto
        {
            "phone": "3008888888",
            "driver_info": {"first_name": "Sofía", "last_name": "Ramírez", "birth_date": date(1992, 11, 25), "email": "sofia.ramirez@example.com"},
            "vehicle_info": {"brand": "Honda", "model": "CB 190R", "model_year": 2022, "color": "Azul", "plate": "SOF012", "vehicle_type": "Motorcycle"}
        }
    ]

    # Obtener tipos de vehículo y documentos
    car_type = session.exec(select(VehicleType).where(VehicleType.name == "Car")).first()
    moto_type = session.exec(select(VehicleType).where(VehicleType.name == "Motorcycle")).first()
    
    license_type = session.exec(select(DocumentType).where(DocumentType.name == "license")).first()
    soat_type = session.exec(select(DocumentType).where(DocumentType.name == "soat")).first()
    tech_type = session.exec(select(DocumentType).where(DocumentType.name == "technical_inspections")).first()
    card_type = session.exec(select(DocumentType).where(DocumentType.name == "property_card")).first()

    completed_drivers = []

    for config in driver_configs:
        # Buscar el usuario por teléfono
        user = session.exec(select(User).where(User.phone_number == config["phone"])).first()
        if not user:
            continue

        # Verificar si ya tiene DriverInfo
        existing_driver_info = session.exec(select(DriverInfo).where(DriverInfo.user_id == user.id)).first()
        if existing_driver_info:
            continue

        # Crear DriverInfo
        driver_info = DriverInfo(
            user_id=user.id,
            first_name=config["driver_info"]["first_name"],
            last_name=config["driver_info"]["last_name"],
            birth_date=config["driver_info"]["birth_date"],
            email=config["driver_info"]["email"],
            selfie_url=user.selfie_url
        )
        session.add(driver_info)
        session.commit()
        session.refresh(driver_info)

        # Crear transacción BONUS
        bonus_transaction = Transaction(
            user_id=user.id,
            income=20000,
            expense=0,
            type=TransactionType.BONUS,
            client_request_id=None,
            id_withdrawal=None,
            is_confirmed=True,
            date=datetime.utcnow()
        )
        session.add(bonus_transaction)

        # Crear registro de monto verificado
        verify_mount = VerifyMount(
            user_id=user.id,
            mount=20000
        )
        session.add(verify_mount)
        session.commit()

        # Crear VehicleInfo
        vehicle_type_id = car_type.id if config["vehicle_info"]["vehicle_type"] == "Car" else moto_type.id
        vehicle_info = VehicleInfo(
            brand=config["vehicle_info"]["brand"],
            model=config["vehicle_info"]["model"],
            model_year=config["vehicle_info"]["model_year"],
            color=config["vehicle_info"]["color"],
            plate=config["vehicle_info"]["plate"],
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
                    status=DriverStatus.APPROVED,
                    expiration_date=doc["expiration_date"],
                    driver_info_id=driver_info.id,
                    vehicle_info_id=vehicle_info.id
                )
                session.add(new_doc)

                # Copiar archivos demo
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

        completed_drivers.append(user)

    session.commit()
    print(f"✅ Configurados {len(completed_drivers)} conductores con documentos, transacciones y montos")
    return completed_drivers


def create_client_requests(session: Session, users, drivers):
    """3. Crear 12 client_request (6 moto, 6 carro)"""
    
    # Coordenadas de prueba en Bogotá
    TEST_COORDINATES = {
        "pickup_points": [
            {"lat": 4.718136, "lng": -74.073170, "description": "Suba Bogotá"},
            {"lat": 4.702468, "lng": -74.109776, "description": "Santa Rosita Engativa"},
            {"lat": 4.648270, "lng": -74.061890, "description": "Chapinero Centro"},
            {"lat": 4.609710, "lng": -74.151750, "description": "Kennedy Central"},
            {"lat": 4.760032, "lng": -74.037677, "description": "Zona Rosa"},
            {"lat": 4.628594, "lng": -74.064865, "description": "Universidad Nacional"},
            {"lat": 4.686419, "lng": -74.055969, "description": "Zona T"},
            {"lat": 4.570868, "lng": -74.297333, "description": "Fontibón"},
            {"lat": 4.638618, "lng": -74.082618, "description": "La Candelaria"},
            {"lat": 4.595447, "lng": -74.166527, "description": "Corabastos"},
            {"lat": 4.711486, "lng": -74.072502, "description": "Plaza de las Américas"},
            {"lat": 4.624335, "lng": -74.063611, "description": "Museo del Oro"}
        ],
        "destinations": [
            {"lat": 4.598100, "lng": -74.076100, "description": "Centro Internacional"},
            {"lat": 4.798100, "lng": -74.046100, "description": "Centro Comercial Andino"},
            {"lat": 4.698100, "lng": -74.126100, "description": "Centro Comercial Metrópolis"},
            {"lat": 4.558100, "lng": -74.146100, "description": "Portal Sur"},
            {"lat": 4.676220, "lng": -74.048066, "description": "Aeropuerto El Dorado"},
            {"lat": 4.601009, "lng": -74.065863, "description": "Terminal de Transporte"},
            {"lat": 4.711111, "lng": -74.072222, "description": "Centro Comercial Titán Plaza"},
            {"lat": 4.590278, "lng": -74.132500, "description": "Hospital Kennedy"},
            {"lat": 4.657889, "lng": -74.054167, "description": "Universidad Javeriana"},
            {"lat": 4.628056, "lng": -74.064722, "description": "Palacio de Justicia"},
            {"lat": 4.715278, "lng": -74.036111, "description": "Centro Comercial Santafé"},
            {"lat": 4.624722, "lng": -74.063889, "description": "Plaza Bolívar"}
        ]
    }

    # Obtener tipos de servicio
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

    clients = users['clients'][:12]  # Primeros 12 clientes
    requests = []

    for i in range(12):
        client = clients[i]
        pickup = TEST_COORDINATES["pickup_points"][i]
        destination = TEST_COORDINATES["destinations"][i]
        
        # 6 de moto (índices pares) y 6 de carro (índices impares)
        type_service_id = moto_service.id if i % 2 == 0 else car_service.id
        
        request = ClientRequest(
            id_client=client.id,
            type_service_id=type_service_id,
            fare_offered=random.randint(15000, 25000),
            pickup_description=pickup["description"],
            destination_description=destination["description"],
            pickup_position=from_shape(Point(pickup["lng"], pickup["lat"]), srid=4326),
            destination_position=from_shape(Point(destination["lng"], destination["lat"]), srid=4326),
            payment_method_id=random.randint(1, 3),
            status=StatusEnum.CREATED
        )
        
        session.add(request)
        requests.append(request)

    session.commit()
    for req in requests:
        session.refresh(req)
    
    print(f"✅ Creadas {len(requests)} solicitudes (6 moto, 6 carro)")
    return requests


def create_driver_offers(session: Session, drivers, requests):
    """4. Drivers realizan ofertas sobre los requests"""
    
    # Obtener información de vehículos de los conductores
    driver_vehicle_types = {}
    for driver in drivers:
        driver_info = session.exec(select(DriverInfo).where(DriverInfo.user_id == driver.id)).first()
        if driver_info:
            vehicle_info = session.exec(select(VehicleInfo).where(VehicleInfo.driver_info_id == driver_info.id)).first()
            if vehicle_info:
                vehicle_type = session.exec(select(VehicleType).where(VehicleType.id == vehicle_info.vehicle_type_id)).first()
                driver_vehicle_types[driver.id] = vehicle_type.name

    offers_created = 0
    
    for request in requests:
        # Obtener el tipo de servicio del request
        type_service = session.exec(select(TypeService).where(TypeService.id == request.type_service_id)).first()
        vehicle_type = session.exec(select(VehicleType).where(VehicleType.id == type_service.vehicle_type_id)).first()
        
        # Filtrar conductores que pueden atender este tipo de servicio
        eligible_drivers = [
            driver for driver in drivers 
            if driver.id in driver_vehicle_types and driver_vehicle_types[driver.id] == vehicle_type.name
        ]
        
        # Cada request recibe ofertas de 1-3 conductores elegibles
        num_offers = random.randint(1, min(3, len(eligible_drivers)))
        selected_drivers = random.sample(eligible_drivers, num_offers)
        
        for driver in selected_drivers:
            fare_offer = request.fare_offered + random.randint(1000, 5000)
            trip_offer = DriverTripOffer(
                id_driver=driver.id,
                id_client_request=request.id,
                fare_offer=fare_offer,
                time=random.randint(10, 30),
                distance=random.randint(3, 15)
            )
            session.add(trip_offer)
            offers_created += 1

    session.commit()
    print(f"✅ Creadas {offers_created} ofertas de conductores")


def complete_some_requests(session: Session, drivers, requests):
    """5. Completar 5 client_request (asignar driver, marcar como PAID, etc)"""
    
    # Obtener información de vehículos de los conductores
    driver_vehicle_types = {}
    for driver in drivers:
        driver_info = session.exec(select(DriverInfo).where(DriverInfo.user_id == driver.id)).first()
        if driver_info:
            vehicle_info = session.exec(select(VehicleInfo).where(VehicleInfo.driver_info_id == driver_info.id)).first()
            if vehicle_info:
                vehicle_type = session.exec(select(VehicleType).where(VehicleType.id == vehicle_info.vehicle_type_id)).first()
                driver_vehicle_types[driver.id] = vehicle_type.name

    # Seleccionar 5 requests para completar
    requests_to_complete = requests[:5]
    completed_count = 0

    for request in requests_to_complete:
        # Obtener ofertas para este request
        offers = session.exec(
            select(DriverTripOffer).where(DriverTripOffer.id_client_request == request.id)
        ).all()
        
        if offers:
            # Seleccionar una oferta aleatoria
            selected_offer = random.choice(offers)
            
            # Completar la solicitud
            request.id_driver_assigned = selected_offer.id_driver
            request.fare_assigned = selected_offer.fare_offer
            request.client_rating = round(random.uniform(4.0, 5.0), 1)
            request.driver_rating = round(random.uniform(4.0, 5.0), 1)
            request.review = random.choice([
                "Excelente servicio",
                "Muy buen conductor",
                "Puntual y amable",
                "Viaje cómodo y seguro",
                "Recomendado",
                "Muy profesional"
            ])
            request.status = StatusEnum.PAID
            
            session.add(request)
            completed_count += 1

    session.commit()
    print(f"✅ Completadas {completed_count} solicitudes con estado PAID")


def init_referral_data(session: Session, users):
    """Inicializa los datos de referidos"""
    referral_data = [
        {"user_phone": "3003333333", "referrer_phone": "3002222222"},
        {"user_phone": "3004444444", "referrer_phone": "3001111111"},
        {"user_phone": "3004444445", "referrer_phone": "3001111111"},
        {"user_phone": "3004444446", "referrer_phone": "3003333333"},
        {"user_phone": "3004444447", "referrer_phone": "3004444446"},
        {"user_phone": "3004444448", "referrer_phone": "3004442444"},
        {"user_phone": "3004444449", "referrer_phone": "3004442444"},
        {"user_phone": "3004444450", "referrer_phone": "3004884450"},
        {"user_phone": "3004444451", "referrer_phone": "3004444450"},
        {"user_phone": "3004444452", "referrer_phone": "3004444451"},
        {"user_phone": "3334444452", "referrer_phone": "3004444452"},
        {"user_phone": "3004444453", "referrer_phone": "3004444446"},
        {"user_phone": "3004444454", "referrer_phone": "3004444449"},
        {"user_phone": "3004444455", "referrer_phone": "3004444453"},
        {"user_phone": "3004444456", "referrer_phone": "3004444447"},
        {"user_phone": "3004444457", "referrer_phone": "3004444448"},
        {"user_phone": "3004444458", "referrer_phone": "3001111111"},
        {"user_phone": "3004444459", "referrer_phone": "3004444454"},
        {"user_phone": "3004444460", "referrer_phone": "3004444449"},
    ]

    existing_referrals = session.exec(select(Referral)).all()
    if existing_referrals:
        return

    for data in referral_data:
        user = session.exec(select(User).where(User.phone_number == data["user_phone"])).first()
        referrer = session.exec(select(User).where(User.phone_number == data["referrer_phone"])).first()

        if user and referrer:
            referral = Referral(
                user_id=user.id,
                referred_by_id=referrer.id
            )
            session.add(referral)

    session.commit()
    print("✅ Datos de referidos inicializados")


def create_driver_positions(session: Session, drivers):
    """Crear posiciones de conductores"""
    driver_positions = {
        "3009999999": {"lat": 4.708822, "lng": -74.076542},  # demo_driver
        "3148780278": {"lat": 4.712345, "lng": -74.078901},  # prueba_conductor
        "3005555555": {"lat": 4.715678, "lng": -74.081234},  # Roberto
        "3006666666": {"lat": 4.719012, "lng": -74.083567},  # Laura
        "3007777777": {"lat": 4.722345, "lng": -74.085890},  # Pedro
        "3008888888": {"lat": 4.725678, "lng": -74.088123},  # Sofía
    }

    for driver in drivers:
        if driver.phone_number in driver_positions:
            coords = driver_positions[driver.phone_number]
            position = DriverPosition(
                id_driver=driver.id,
                position=from_shape(Point(coords["lng"], coords["lat"]), srid=4326)
            )
            session.merge(position)

    session.commit()
    print("✅ Posiciones de conductores creadas")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def init_data():
    """Inicializa los datos básicos de la aplicación."""
    session = Session(engine)

    try:
        print("🚀 Iniciando configuración de datos...")
        
        # Configuración básica
        init_roles()
        init_document_types()
        init_vehicle_types(engine)
        
        # Inicializar tipos de servicio
        type_service_service = TypeServiceService(session)
        type_service_service.init_default_types()

        init_time_distance_values(engine)
        init_project_settings()
        init_payment_methods(session)
        # 1. Crear todos los usuarios (clientes y conductores)
        users = create_all_users(session)

        # 2. Crear y definir todos los drivers con documentos, transacciones y monto
        drivers = create_all_drivers(session, users)

        # 3. Crear 12 client_request (6 moto, 6 carro)
        requests = create_client_requests(session, users, drivers)

        # 4. Drivers realizan ofertas sobre los requests
        create_driver_offers(session, drivers, requests)

        # 5. Completar 5 client_request (asignar driver, marcar como PAID, etc)
        complete_some_requests(session, drivers, requests)

        # Datos adicionales
        init_referral_data(session, users)
        create_driver_positions(session, drivers)
        create_admin(session)

        session.commit()
        print("✅ Inicialización completada correctamente.")

    except Exception as e:
        session.rollback()
        print(f"❌ Error en la inicialización: {e}")
        raise
    finally:
        session.close()