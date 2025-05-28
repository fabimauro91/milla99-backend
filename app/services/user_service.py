from sqlmodel import Session, select
from app.models.user import User, UserCreate, UserUpdate
from app.models.role import Role
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.referral_chain import Referral
from typing import List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import selectinload
from datetime import datetime
import os
from app.core.config import settings
import uuid
from uuid import UUID


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user_data: UserCreate) -> User:
        with self.session.begin():
            # Check for existing phone (country_code + phone_number)
            existing_user = self.session.exec(
                select(User).where(
                    User.country_code == user_data.country_code,
                    User.phone_number == user_data.phone_number
                )
            ).first()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this phone number already exists."
                )

            user = User.model_validate(user_data.model_dump())
            self.session.add(user)
            self.session.flush()  # Para obtener el id antes del commit

            # Asignar el rol CLIENT por defecto
            client_role = self.session.exec(
                select(Role).where(Role.id == "CLIENT")).first()
            if not client_role:
                raise HTTPException(
                    status_code=500, detail="Rol CLIENT no existe")

            # La relación se crea automáticamente a través del link_model
            user.roles.append(client_role)

            # Si hay un token de referido, validarlo y crear la relación de referido
            if user_data.referral_phone:
                referral_user = self.session.exec(
                    select(User).where(
                        User.phone_number == user_data.referral_phone
                    )
                ).first()
                if referral_user:
                    referral = Referral(
                        user_id=user.id, referred_by_id=referral_user.id)
                    self.session.add(referral)

            # Actualizar el estado de la relación a través del link_model
            user_role = self.session.exec(
                select(UserHasRole).where(
                    UserHasRole.id_user == user.id,
                    UserHasRole.id_rol == client_role.id
                )
            ).first()
            if user_role:
                user_role.is_verified = True
                user_role.status = RoleStatus.APPROVED
                user_role.verified_at = datetime.utcnow()
                self.session.add(user_role)

            self.session.add(user)
            # El commit se hace automáticamente al salir del with

        return user

    def _save_user_selfie(self, uploader, user_id: UUID, selfie: UploadFile):
        """Guarda la selfie en static/uploads/users/{user_id}/selfie_<uuid>.jpg"""
        selfie_dir = os.path.join("static", "uploads", "users", str(user_id))
        os.makedirs(selfie_dir, exist_ok=True)
        ext = os.path.splitext(selfie.filename)[1] or ".jpg"
        unique_name = f"selfie_{uuid.uuid4().hex}{ext}"
        selfie_path = os.path.join(selfie_dir, unique_name)
        with open(selfie_path, "wb") as f:
            f.write(selfie.file.read())
        url = f"{settings.STATIC_URL_PREFIX}/users/{user_id}/{unique_name}"
        return {"url": url}

    def get_users(self) -> list[User]:
        return self.session.exec(select(User)).all()

    def get_user(self, user_id: UUID) -> User:
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        user = self.get_user(user_id)
        user_data_dict = user_data.model_dump(exclude_unset=True)
        user.sqlmodel_update(user_data_dict)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: UUID) -> dict:
        user = self.get_user(user_id)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already inactive."
            )
        user.is_active = False
        self.session.add(user)
        self.session.commit()
        return {"message": "User deactivated (soft deleted) successfully"}

    def verify_user(self, user_id: UUID) -> User:
        user = self.get_user(user_id)
        if user.is_verified_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already verified."
            )
        user.is_verified_phone = True
        user.is_active = True
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_selfie(self, user_id: UUID, selfie: UploadFile):
        user = self.get_user(user_id)
        selfie_info = self._save_user_selfie(None, user.id, selfie)
        user.selfie_url = selfie_info["url"]
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return {"selfie_url": user.selfie_url}
