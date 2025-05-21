from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from app.models.driver_payment import DriverPayment, DriverPaymentCreate, DriverPaymentUpdate, PaymentStatus
from app.models.user import User
from app.models.driver_transaction import DriverTransaction, TransactionType
from app.models.role import Role
from fastapi import HTTPException
from datetime import datetime


class DriverPaymentService:
    def __init__(self, db: Session):
        self.db = db

    def _is_admin(self, user: User) -> bool:
        """Verifica si un usuario tiene el rol de administrador."""
        admin_role = self.db.exec(
            select(Role).where(Role.id == "ADMIN")
        ).first()
        return admin_role is not None and admin_role in user.roles

    def create_payment(
        self,
        payment_data: DriverPaymentCreate,
        current_user: User
    ) -> DriverPayment:
        """Crea una nueva cuenta de pago para un conductor."""
        # Verificar que el usuario existe
        user = self.db.get(User, payment_data.id_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verificar que el usuario es conductor (tiene el rol DRIVER)
        driver_role = self.db.exec(
            select(Role).where(Role.id == "DRIVER")
        ).first()
        if not driver_role or driver_role not in user.roles:
            raise HTTPException(status_code=400, detail="User is not a driver")

        # Verificar que el conductor no tenga ya una cuenta de pago
        existing_payment = self.db.exec(
            select(DriverPayment).where(
                DriverPayment.id_user == payment_data.id_user)
        ).first()
        if existing_payment:
            raise HTTPException(
                status_code=400, detail="Driver already has a payment account")

        # Crear la cuenta de pago
        payment_dict = payment_data.dict()
        payment_dict.update({
            "status": PaymentStatus.ACTIVE,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        payment = DriverPayment(**payment_dict)

        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def get_payment(self, payment_id: int) -> DriverPayment:
        """Obtiene una cuenta de pago por su ID."""
        payment = self.db.get(DriverPayment, payment_id)
        if not payment:
            raise HTTPException(
                status_code=404, detail="Payment account not found")
        return payment

    def get_payments(
        self,
        user_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DriverPayment]:
        """Obtiene una lista de cuentas de pago con filtros opcionales."""
        query = select(DriverPayment)

        if user_id:
            query = query.where(DriverPayment.id_user == user_id)
        if status:
            query = query.where(DriverPayment.status == status)

        query = query.order_by(DriverPayment.created_at.desc())
        query = query.offset(skip).limit(limit)

        return list(self.db.exec(query))

    def update_payment(
        self,
        payment_id: int,
        payment_data: DriverPaymentUpdate,
        current_user: User
    ) -> DriverPayment:
        """Actualiza una cuenta de pago existente."""
        payment = self.get_payment(payment_id)

        # Solo los administradores pueden actualizar el estado
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=403, detail="Only admins can update payment status")

        # Solo permitir actualizar ciertos campos
        update_data = payment_data.dict(exclude_unset=True)

        # Si se está actualizando el estado
        if "status" in update_data:
            new_status = update_data["status"]

            # No se puede cambiar el estado de una cuenta bloqueada
            if payment.status == PaymentStatus.BLOCKED:
                raise HTTPException(
                    status_code=400, detail="Cannot update blocked payment account")

            # Si se está bloqueando la cuenta, verificar que no tenga transacciones pendientes
            if new_status == PaymentStatus.BLOCKED:
                pending_transactions = self.db.exec(
                    select(DriverTransaction)
                    .where(DriverTransaction.id_payment == payment_id)
                    .where(DriverTransaction.status == "pending")
                ).all()
                if pending_transactions:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot block payment account with pending transactions"
                    )

        # Actualizar la cuenta
        for key, value in update_data.items():
            setattr(payment, key, value)

        payment.updated_at = datetime.utcnow()

        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def get_user_payment(self, user_id: int) -> Optional[DriverPayment]:
        """Obtiene la cuenta de pago de un usuario específico."""
        return self.db.exec(
            select(DriverPayment).where(DriverPayment.id_user == user_id)
        ).first()

    def get_payment_summary(self, payment_id: int) -> dict:
        """Obtiene un resumen de la cuenta de pago con totales por tipo de transacción."""
        payment = self.get_payment(payment_id)

        # Obtener todas las transacciones de la cuenta
        transactions = self.db.exec(
            select(DriverTransaction)
            .where(DriverTransaction.id_payment == payment_id)
            .order_by(DriverTransaction.created_at.desc())
        ).all()

        summary = {
            "payment_id": payment.id,
            "user_id": payment.id_user,
            "status": payment.status,
            "available_balance": payment.available_balance,
            "withdrawable_balance": payment.withdrawable_balance,
            "total_transactions": len(transactions),
            "by_type": {}
        }

        # Agrupar transacciones por tipo
        for transaction in transactions:
            if transaction.transaction_type not in summary["by_type"]:
                summary["by_type"][transaction.transaction_type] = {
                    "count": 0,
                    "total": Decimal("0")
                }

            summary["by_type"][transaction.transaction_type]["count"] += 1
            summary["by_type"][transaction.transaction_type]["total"] += transaction.amount

        return summary

    def add_welcome_bonus(
        self,
        payment_id: int,
        bonus_amount: Decimal,
        current_user: User
    ) -> DriverTransaction:
        """Agrega un bono de bienvenida a la cuenta de pago automáticamente."""
        payment = self.get_payment(payment_id)

        # Verificar que la cuenta esté activa
        if payment.status != PaymentStatus.ACTIVE:
            raise HTTPException(
                status_code=400, detail="Payment account is not active")

        # Verificar que no tenga transacciones previas de bono
        existing_transactions = self.db.exec(
            select(DriverTransaction)
            .where(DriverTransaction.id_payment == payment_id)
            .where(DriverTransaction.transaction_type == TransactionType.BONUS)
        ).all()

        if existing_transactions:
            raise HTTPException(
                status_code=400, detail="Welcome bonus already added")

        # Crear la transacción de bono
        transaction = DriverTransaction(
            id_payment=payment_id,
            id_user=payment.id_user,
            transaction_type=TransactionType.BONUS,
            amount=bonus_amount,
            description="Welcome bonus",
            status="completed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Actualizar balances: solo available_balance
        payment.available_balance += bonus_amount
        # payment.withdrawable_balance += bonus_amount  # Ya no se suma aquí
        payment.total_balance = payment.available_balance
        payment.updated_at = datetime.utcnow()

        self.db.add(transaction)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def get_payment_by_user_id(self, user_id: int) -> Optional[DriverPayment]:
        """Obtener la cuenta de pago de un conductor por su ID"""
        statement = select(DriverPayment).where(
            DriverPayment.id_user == user_id)
        return self.db.exec(statement).first()

    def get_payment_by_id(self, payment_id: int) -> Optional[DriverPayment]:
        """Obtener una cuenta de pago por su ID"""
        return self.db.get(DriverPayment, payment_id)

    def update_balances(self, payment_id: int,
                        total_change: Decimal = Decimal('0'),
                        available_change: Decimal = Decimal('0'),
                        pending_change: Decimal = Decimal('0')) -> Optional[DriverPayment]:
        """Actualizar los balances de una cuenta de pago"""
        db_payment = self.get_payment_by_id(payment_id)
        if not db_payment:
            return None

        db_payment.total_balance += total_change
        db_payment.available_balance += available_change
        db_payment.pending_balance += pending_change

        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def get_all_payments(self) -> List[DriverPayment]:
        """Obtener todas las cuentas de pago"""
        statement = select(DriverPayment)
        return list(self.db.exec(statement))

    def delete_payment(self, payment_id: int) -> bool:
        """Eliminar una cuenta de pago"""
        db_payment = self.get_payment_by_id(payment_id)
        if not db_payment:
            return False

        self.db.delete(db_payment)
        self.db.commit()
        return True
