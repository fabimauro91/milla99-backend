from sqlmodel import Session, select
from app.models.role import Role
from app.models.user import User
from app.models.user_has_roles import UserHasRole
from app.models.driver_data import DriverData, DriverStatus
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

def init_test_driver():
    with Session(engine) as session:
        # Crear usuario conductor de prueba
        driver_user = session.exec(select(User).where(
            User.full_name == "prueba_conductor")).first()

        if not driver_user:
            driver_user = User(
                full_name="prueba_conductor",
                country_code="+57",
                phone_number=settings.TEST_DRIVER_PHONE,  # Asegúrate de tener esta configuración
                is_verified=True,
                is_active=True
            )
            session.add(driver_user)
            session.commit()
            session.refresh(driver_user)

        # Asignar el rol DRIVER
        driver_role = session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        if driver_role and driver_role not in driver_user.roles:
            driver_user.roles.append(driver_role)
            session.add(driver_user)
            session.commit()

        # Crear DriverData para el conductor de prueba
        driver_data = session.exec(
            select(DriverData).where(DriverData.user_id == driver_user.id)
        ).first()

        if not driver_data:
            driver_data = DriverData(
                user_id=driver_user.id,
                status=DriverStatus.APPROVED,  # O el estado que prefieras
                qualification=5,  # Calificación de ejemplo
                # Los IDs de documentos (soat, technomechanics, etc.) se pueden agregar después
                # cuando implementes esos modelos
            )
            session.add(driver_data)
            session.commit()            


def init_data():
    init_roles()
    init_test_user()
