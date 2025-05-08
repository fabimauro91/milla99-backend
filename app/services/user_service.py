from sqlmodel import Session, select
from app.models.user import User, UserCreate, UserUpdate
from app.models.role import Role
from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload


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

            # Asignar los roles que vengan en el request
            if user_data.roles:
                for role_id in user_data.roles:
                    role = self.session.exec(
                        select(Role).where(Role.id == role_id)).first()
                    if not role:
                        raise HTTPException(
                            status_code=400, detail=f"Rol {role_id} no existe")
                    user.roles.append(role)
            else:
                raise HTTPException(
                    status_code=400, detail="Debes enviar al menos un rol")

            self.session.add(user)
            # El commit se hace automáticamente al salir del with

        return user

    def get_users(self) -> list[User]:
        return self.session.exec(select(User)).all()

    def get_user(self, user_id: int) -> User:
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        user = self.get_user(user_id)
        user_data_dict = user_data.model_dump(exclude_unset=True)
        user.sqlmodel_update(user_data_dict)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: int) -> dict:
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

    def verify_user(self, user_id: int) -> User:
        user = self.get_user(user_id)
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already verified."
            )
        user.is_verified = True
        user.is_active = True
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
