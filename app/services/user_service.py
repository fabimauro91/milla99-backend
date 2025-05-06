from sqlmodel import Session, select
from app.models.user import User, UserCreate, UserUpdate
from fastapi import HTTPException, status


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user_data: UserCreate) -> User:
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
        self.session.commit()
        self.session.refresh(user)
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
        self.session.delete(user)
        self.session.commit()
        return {"message": "User deleted successfully"}

    def verify_user(self, user_id: int) -> User:
        user = self.get_user(user_id)
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already verified."
            )
        user.is_verified = True
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
