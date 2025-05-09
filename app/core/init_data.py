from sqlmodel import Session, select
from app.models.role import Role
from app.models.user import User, UserCreate
from app.models.user_has_roles import UserHasRole
from app.models.vehicle_type import VehicleType
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
                is_verified=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        # Asignar el rol CLIENT si no lo tiene
        client_role = session.exec(
            select(Role).where(Role.id == "CLIENT")).first()
        if client_role and client_role not in user.roles:
            user.roles.append(client_role)
            session.add(user)
            session.commit()


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
    init_test_user()
    init_vehicle_types()