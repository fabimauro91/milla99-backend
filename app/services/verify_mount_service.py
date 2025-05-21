from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.verify_mount import (
    VerifyMount,
    VerifyMountCreate,
    VerifyMountUpdate,
    VerifyMountStatus,
    PaymentMethod
)
from app.models.user import User
from app.models.driver_payment import DriverPayment, PaymentStatus


class VerifyMountService:
    def __init__(self, db: Session):
        self.db = db

    def create_verify_mount(
        self,
        verify_mount_data: VerifyMountCreate,
        current_user: User
    ) -> VerifyMount:
        """Crea una nueva solicitud de verificación de monto."""
        # Verificar que el pago existe y está activo
        payment = self.db.get(DriverPayment, verify_mount_data.id_payment)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status != PaymentStatus.ACTIVE:
            raise HTTPException(
                status_code=400, detail="Payment account is not active")

        # Verificar que el usuario existe
        user = self.db.get(User, verify_mount_data.id_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Crear la verificación
        verify_mount = VerifyMount(
            **verify_mount_data.dict(),
            status=VerifyMountStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(verify_mount)
        self.db.commit()
        self.db.refresh(verify_mount)

        return verify_mount

    def get_verify_mount(self, verify_mount_id: int) -> VerifyMount:
        """Obtiene una verificación de monto por su ID."""
        verify_mount = self.db.get(VerifyMount, verify_mount_id)
        if not verify_mount:
            raise HTTPException(
                status_code=404, detail="Verify mount not found")
        return verify_mount

    def get_verify_mounts(
        self,
        user_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        status: Optional[VerifyMountStatus] = None,
        payment_method: Optional[PaymentMethod] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[VerifyMount]:
        """Obtiene una lista de verificaciones de monto con filtros opcionales."""
        query = select(VerifyMount)

        if user_id:
            query = query.where(VerifyMount.id_user == user_id)
        if payment_id:
            query = query.where(VerifyMount.id_payment == payment_id)
        if status:
            query = query.where(VerifyMount.status == status)
        if payment_method:
            query = query.where(VerifyMount.payment_method == payment_method)
        if start_date:
            query = query.where(VerifyMount.created_at >= start_date)
        if end_date:
            query = query.where(VerifyMount.created_at <= end_date)

        query = query.order_by(VerifyMount.created_at.desc())
        query = query.offset(skip).limit(limit)

        return list(self.db.exec(query))

    def update_verify_mount(
        self,
        verify_mount_id: int,
        verify_mount_data: VerifyMountUpdate,
        current_user: User
    ) -> VerifyMount:
        """Actualiza una verificación de monto existente."""
        verify_mount = self.get_verify_mount(verify_mount_id)

        # Solo los administradores pueden actualizar el estado
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Only admins can update verify mount status")

        # Solo permitir actualizar ciertos campos
        update_data = verify_mount_data.dict(exclude_unset=True)

        # Si se está actualizando el estado
        if "status" in update_data:
            new_status = update_data["status"]

            # No se puede cambiar el estado de una verificación ya verificada
            if verify_mount.status == VerifyMountStatus.VERIFIED:
                raise HTTPException(
                    status_code=400, detail="Cannot update verified mount")

            # Si se está verificando, registrar quién lo verificó y cuándo
            if new_status == VerifyMountStatus.VERIFIED:
                update_data["verified_by"] = current_user.id
                update_data["verified_at"] = datetime.utcnow()
            elif new_status == VerifyMountStatus.REJECTED:
                update_data["verified_by"] = current_user.id
                update_data["verified_at"] = datetime.utcnow()

        # Actualizar la verificación
        for key, value in update_data.items():
            setattr(verify_mount, key, value)

        verify_mount.updated_at = datetime.utcnow()

        self.db.add(verify_mount)
        self.db.commit()
        self.db.refresh(verify_mount)

        return verify_mount

    def get_pending_verify_mounts(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[VerifyMount]:
        """Obtiene las verificaciones de monto pendientes."""
        return self.get_verify_mounts(
            status=VerifyMountStatus.PENDING,
            skip=skip,
            limit=limit
        )

    def get_user_verify_mounts(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[VerifyMount]:
        """Obtiene las verificaciones de monto de un usuario específico."""
        return self.get_verify_mounts(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
