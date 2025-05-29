from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.core.db import get_session
from app.services.login_admin_service import authenticate_admin, create_admin_token
from pydantic import BaseModel

router = APIRouter(prefix="/login-admin",
                   tags=["ADMIN: login"])

class AdminLoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login_admin(data: AdminLoginRequest, session: Session = Depends(get_session)):
    admin = authenticate_admin(session, data.email, data.password)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    token = create_admin_token(admin)
    return {"access_token": token, "token_type": "bearer", "role": admin.role} 