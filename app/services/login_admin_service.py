from sqlmodel import Session, select
from app.models.administrador import Administrador
from passlib.hash import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def authenticate_admin(session: Session, email: str, password: str):
    admin = session.exec(select(Administrador).where(Administrador.email == email)).first()
    if not admin or not bcrypt.verify(password, admin.password):
        return None
    return admin

def create_admin_token(admin: Administrador):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(admin.id),
        "email": admin.email,
        "role": admin.role,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt 