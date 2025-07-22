from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from decimal import Decimal
import logging

from app.models.user import User
from app.models.verify_mount import VerifyMount
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.deleted_user import DeletedUser

logger = logging.getLogger(__name__)


def check_driver_bonus_eligibility(session: Session, user_id: UUID) -> dict:
    """
    Verifica si un conductor es elegible para recibir el bono inicial.

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario conductor

    Returns:
        dict: Información sobre elegibilidad y monto del bono
    """
    try:
        # Obtener información del usuario
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404, detail="Usuario no encontrado")

        # Verificar si es conductor
        driver_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id,
            UserHasRole.id_rol == "DRIVER"
        ).first()

        if not driver_role:
            return {
                "eligible": False,
                "reason": "Usuario no es conductor",
                "bonus_amount": 0
            }

        # Verificar si el teléfono pertenece a un usuario eliminado
        deleted_user = session.query(DeletedUser).filter(
            DeletedUser.phone_number == user.phone_number
        ).first()

        # Si existe un usuario eliminado con este teléfono Y el usuario actual es conductor
        if deleted_user and driver_role:
            logger.warning(
                f"🚫 Conductor {user_id} ({user.phone_number}) intentó recibir bono pero fue eliminado previamente")
            return {
                "eligible": False,
                "reason": f"Este conductor fue eliminado el {deleted_user.deleted_at.strftime('%d/%m/%Y')}. No puede recibir bono nuevamente.",
                "bonus_amount": 0,
                "original_balance": float(deleted_user.original_balance)
            }

        # Verificar si ya tiene balance (ya recibió bono)
        existing_balance = session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id
        ).first()

        if existing_balance and float(existing_balance.mount) > 0:
            return {
                "eligible": False,
                "reason": "Conductor ya tiene balance activo",
                "bonus_amount": 0,
                "current_balance": float(existing_balance.mount)
            }

        # Es elegible para bono
        bonus_amount = 20000  # $20,000 COP
        return {
            "eligible": True,
            "reason": "Conductor elegible para bono inicial",
            "bonus_amount": bonus_amount
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error verificando elegibilidad de bono para conductor {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error interno verificando elegibilidad")


def apply_driver_bonus(session: Session, user_id: UUID) -> dict:
    """
    Aplica el bono inicial a un conductor elegible.

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario conductor

    Returns:
        dict: Resultado de la aplicación del bono
    """
    try:
        # Verificar elegibilidad
        eligibility = check_driver_bonus_eligibility(session, user_id)

        if not eligibility["eligible"]:
            raise HTTPException(
                status_code=400,
                detail=eligibility["reason"]
            )

        bonus_amount = eligibility["bonus_amount"]

        # Crear o actualizar balance
        existing_balance = session.query(VerifyMount).filter(
            VerifyMount.id_user == user_id
        ).first()

        if existing_balance:
            existing_balance.balance = Decimal(str(bonus_amount))
            session.add(existing_balance)
        else:
            new_balance = VerifyMount(
                id_user=user_id,
                balance=Decimal(str(bonus_amount))
            )
            session.add(new_balance)

        session.commit()

        logger.info(
            f"✅ Bono de ${bonus_amount} aplicado al conductor {user_id}")

        return {
            "success": True,
            "message": f"Bono de ${bonus_amount} aplicado exitosamente",
            "bonus_amount": bonus_amount,
            "new_balance": bonus_amount
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error aplicando bono al conductor {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Error interno aplicando bono")
