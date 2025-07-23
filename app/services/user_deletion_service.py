from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

from app.models.user import User
from app.models.user_has_roles import UserHasRole
from app.models.transaction import Transaction
from app.models.client_request import ClientRequest
from app.models.driver_trip_offer import DriverTripOffer
from app.models.driver_position import DriverPosition
from app.models.driver_info import DriverInfo
from app.models.vehicle_info import VehicleInfo
from app.models.verify_mount import VerifyMount
from app.models.user_fcm_token import UserFCMToken
from app.models.penality_user import PenalityUser
from app.models.driver_cancellation import DriverCancellation
from app.models.driver_savings import DriverSavings
from app.models.deleted_user import DeletedUser
from app.models.refresh_token import RefreshToken
from app.models.w_verification import Verification

logger = logging.getLogger(__name__)


def delete_user_completely_service(session: Session, user_id: UUID, reason: str = "User request"):
    """
    Elimina completamente un usuario pero mantiene registro mínimo para evitar re-registro

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario a eliminar
        reason: Razón de la eliminación

    Returns:
        dict: Resultado de la eliminación

    Raises:
        HTTPException: Si el usuario no existe o hay error en la eliminación
    """
    try:
        # 1. Obtener información mínima antes de eliminar
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=404, detail="Usuario no encontrado")

        logger.info(
            f"🔄 Iniciando eliminación completa del usuario {user_id} ({user.phone_number})")

        # 2. Obtener balance actual
        try:
            driver_balance = session.query(VerifyMount).filter(
                VerifyMount.user_id == user_id
            ).first()

            balance_amount = float(
                driver_balance.mount) if driver_balance else 0
            logger.info(f"🔍 DEBUG: Balance encontrado: {driver_balance}")
            logger.info(f"🔍 DEBUG: Balance amount: {balance_amount}")

            # Debug adicional para verificar el balance antes de la eliminación
            if driver_balance:
                logger.info(f"🔍 DEBUG: Balance ID: {driver_balance.id}")
                logger.info(
                    f"🔍 DEBUG: Balance user_id: {driver_balance.user_id}")
                logger.info(f"🔍 DEBUG: Balance mount: {driver_balance.mount}")
            else:
                logger.info(
                    f"🔍 DEBUG: No se encontró balance para usuario {user_id}")
        except Exception as e:
            import traceback
            logger.error(f"❌ ERROR obteniendo balance: {str(e)}")
            logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            balance_amount = 0

        # 3. Determinar tipo de usuario
        user_roles = session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id
        ).all()

        user_type = "DRIVER" if any(
            role.id_rol == "DRIVER" for role in user_roles) else "CLIENT"
        logger.info(f"📊 Usuario tipo: {user_type}, Balance: ${balance_amount}")

        # 4. Verificar que no esté ya en deleted_users
        existing_deleted = session.query(DeletedUser).filter(
            DeletedUser.phone_number == user.phone_number
        ).first()

        if existing_deleted:
            raise HTTPException(
                status_code=400,
                detail="Este usuario ya fue eliminado previamente"
            )

        # 5. Crear registro en deleted_users
        deleted_user = DeletedUser(
            phone_number=user.phone_number,
            original_balance=Decimal(str(balance_amount)),
            deletion_reason=reason,
            user_type=user_type
        )
        session.add(deleted_user)

        logger.info(
            f"📝 Registro creado en deleted_users para {user.phone_number}")

        # 6. ELIMINAR TODOS LOS DATOS RELACIONADOS (en orden para evitar FK constraints)

        # Eliminar transacciones
        transactions_deleted = session.query(Transaction).filter(
            Transaction.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminadas {transactions_deleted} transacciones")

        # Eliminar solicitudes de cliente (como cliente)
        client_requests_deleted = session.query(ClientRequest).filter(
            ClientRequest.id_client == user_id
        ).delete()
        logger.info(
            f"🗑️ Eliminadas {client_requests_deleted} solicitudes como cliente")

        # Eliminar solicitudes de cliente (como conductor asignado)
        driver_requests_deleted = session.query(ClientRequest).filter(
            ClientRequest.id_driver_assigned == user_id
        ).delete()
        logger.info(
            f"🗑️ Eliminadas {driver_requests_deleted} solicitudes como conductor")

        # Eliminar ofertas de conductores
        offers_deleted = session.query(DriverTripOffer).filter(
            DriverTripOffer.id_driver == user_id
        ).delete()
        logger.info(f"🗑️ Eliminadas {offers_deleted} ofertas de conductor")

        # Eliminar posiciones de conductor
        positions_deleted = session.query(DriverPosition).filter(
            DriverPosition.id_driver == user_id
        ).delete()
        logger.info(
            f"🗑️ Eliminadas {positions_deleted} posiciones de conductor")

        # Eliminar información de conductor
        driver_info_deleted = session.query(DriverInfo).filter(
            DriverInfo.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminada información de conductor")

        # Eliminar información de vehículo (a través de driver_info)
        # Primero obtener los IDs de los vehículos a eliminar
        vehicle_ids = session.query(VehicleInfo.id).join(DriverInfo).filter(
            DriverInfo.user_id == user_id
        ).all()
        vehicle_ids = [v[0] for v in vehicle_ids]

        # Luego eliminar los vehículos por ID
        if vehicle_ids:
            vehicle_info_deleted = session.query(VehicleInfo).filter(
                VehicleInfo.id.in_(vehicle_ids)
            ).delete(synchronize_session=False)
        else:
            vehicle_info_deleted = 0

        logger.info(f"🗑️ Eliminada información de vehículo")

        # Eliminar balance
        balance_deleted = session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminado balance")

        # Eliminar tokens FCM
        fcm_tokens_deleted = session.query(UserFCMToken).filter(
            UserFCMToken.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminados {fcm_tokens_deleted} tokens FCM")

        # Eliminar penalizaciones
        penalties_deleted = session.query(PenalityUser).filter(
            PenalityUser.id_user == user_id
        ).delete()
        logger.info(f"🗑️ Eliminadas {penalties_deleted} penalizaciones")

        # Eliminar cancelaciones de conductor
        cancellations_deleted = session.query(DriverCancellation).filter(
            DriverCancellation.id_driver == user_id
        ).delete()
        logger.info(
            f"🗑️ Eliminadas {cancellations_deleted} cancelaciones de conductor")

        # Eliminar ahorros de conductor
        savings_deleted = session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminados {savings_deleted} ahorros de conductor")

        # Eliminar refresh tokens
        refresh_tokens_deleted = session.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).delete()
        logger.info(f"🗑️ Eliminados {refresh_tokens_deleted} refresh tokens")

        # Eliminar registros de verificación
        verification_deleted = session.query(Verification).filter(
            Verification.user_id == user_id
        ).delete()
        logger.info(
            f"🗑️ Eliminados {verification_deleted} registros de verificación")

        # Eliminar roles
        roles_deleted = session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id
        ).delete()
        logger.info(f"🗑️ Eliminados {roles_deleted} roles")

        # Verificar balance antes de eliminar usuario
        balance_after_deletions = session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id
        ).first()
        logger.info(
            f"🔍 DEBUG: Balance después de eliminaciones: {balance_after_deletions}")

        # Eliminar usuario principal (último para evitar FK constraints)
        user_deleted = session.query(User).filter(User.id == user_id).delete()
        logger.info(f"🗑️ Eliminado usuario principal")

        # Commit de todos los cambios
        session.commit()

        logger.info(
            f"✅ Usuario {user_id} eliminado completamente. Teléfono {user.phone_number} bloqueado.")

        return {
            "success": True,
            "message": f"Usuario eliminado completamente. Teléfono {user.phone_number} bloqueado para futuros registros.",
            "deleted_at": datetime.utcnow(),
            "phone_number": user.phone_number,
            "user_type": user_type,
            "original_balance": balance_amount
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"❌ Error eliminando usuario {user_id}: {str(e)}")
        logger.error(f"🔍 Traceback completo:\n{error_traceback}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al eliminar usuario: {str(e)}"
        )


def check_deleted_user_registration(session: Session, phone_number: str):
    """
    Verifica si el teléfono pertenece a un usuario eliminado.
    Permite re-registro pero retorna información para evitar abuso del bono.

    Args:
        session: Sesión de base de datos
        phone_number: Número de teléfono a verificar

    Returns:
        dict: Información sobre si puede registrarse y si debe recibir bono
    """
    deleted_user = session.query(DeletedUser).filter(
        DeletedUser.phone_number == phone_number
    ).first()

    if deleted_user:
        result = {
            "can_register": True,
            "no_bonus": True,
            "original_balance": float(deleted_user.original_balance),
            "user_type": deleted_user.user_type,
            "deletion_reason": deleted_user.deletion_reason,
            "deleted_at": deleted_user.deleted_at
        }
        return result

    result = {"can_register": True, "no_bonus": False}
    return result


def restore_deleted_user_balance(session: Session, user_id: UUID, phone_number: str) -> dict:
    """
    Restaura el balance original de un usuario eliminado cuando se re-registra.
    Elimina el registro de deleted_users y restaura el balance en VerifyMount.

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario re-registrado
        phone_number: Número de teléfono del usuario

    Returns:
        dict: Resultado de la restauración
    """
    try:
        # Buscar el registro de usuario eliminado
        deleted_user = session.query(DeletedUser).filter(
            DeletedUser.phone_number == phone_number
        ).first()

        if not deleted_user:
            return {
                "restored": False,
                "message": "No se encontró registro de usuario eliminado",
                "balance_restored": 0
            }

        # Obtener el balance original
        original_balance = float(deleted_user.original_balance)

        # Restaurar el balance en VerifyMount
        existing_balance = session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id
        ).first()

        if existing_balance:
            # Actualizar balance existente
            existing_balance.mount = Decimal(str(original_balance))
            session.add(existing_balance)
        else:
            # Crear nuevo registro de balance
            new_balance = VerifyMount(
                user_id=user_id,
                mount=Decimal(str(original_balance))
            )
            session.add(new_balance)

        # Eliminar el registro de deleted_users
        session.delete(deleted_user)

        # Commit de todos los cambios
        session.commit()

        logger.info(
            f"✅ Balance restaurado para usuario {user_id} ({phone_number}): ${original_balance}")

        return {
            "restored": True,
            "message": f"Balance restaurado exitosamente: ${original_balance}",
            "balance_restored": original_balance,
            "user_type": deleted_user.user_type,
            "deletion_reason": deleted_user.deletion_reason
        }

    except Exception as e:
        session.rollback()
        logger.error(
            f"❌ Error restaurando balance para usuario {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al restaurar balance: {str(e)}"
        )
