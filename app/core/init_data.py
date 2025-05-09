from sqlmodel import Session, select
from datetime import datetime
from app.models.role import Role
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus
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
                is_verified_phone=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        # Asignar el rol CLIENT si no lo tiene y verificarlo
        client_role = session.exec(
            select(Role).where(Role.id == "CLIENT")).first()
        
        if client_role:
            # Verificar si ya existe la relación user-role
            user_role = session.exec(
                select(UserHasRole).where(
                    UserHasRole.id_user == user.id,
                    UserHasRole.id_rol == client_role.id
                )
            ).first()

            if not user_role:
                # Crear nueva relación verificada
                user_role = UserHasRole(
                    id_user=user.id,
                    id_rol=client_role.id,
                    is_verified=True,
                    status=RoleStatus.APPROVED,
                    verified_at=datetime.utcnow()
                )
                session.add(user_role)
                session.commit()


def init_data():
    init_roles()
    init_test_user()
