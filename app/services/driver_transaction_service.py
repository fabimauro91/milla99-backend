from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from app.models.driver_transaction import (
    DriverTransaction, DriverTransactionCreate,
    DriverTransactionUpdate, TransactionType,
    DriverTransactionResponse, TransactionStatus,
    MovementType
)
from app.models.driver_payment import PaymentStatus, DriverPayment
from app.models.verify_mount import VerifyMount, VerifyMountStatus
from app.models.user import User
from fastapi import HTTPException
from datetime import datetime


class DriverTransactionService:
    def __init__(self, db: Session):
        self.db = db

    def create_transaction(
        self,
        id_payment: int,
        id_user: int,
        transaction_type: TransactionType,
        amount: Decimal,
        description: Optional[str] = None,
        discount_amount: Decimal = Decimal("0"),
        reference_id: Optional[str] = None,
        id_verify_mount: Optional[int] = None,
        transaction_date: Optional[datetime] = None
    ) -> DriverTransaction:
        """Crea una nueva transacción y actualiza los balances correspondientes."""
        # Verificar que el pago existe y está activo
        payment = self.db.get(DriverPayment, id_payment)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status != PaymentStatus.ACTIVE:
            raise HTTPException(
                status_code=400, detail="Payment account is not active")

        # Verificar que el usuario existe
        user = self.db.get(User, id_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Si es DEPOSIT y no se pasa id_verify_mount, buscar automáticamente la última verify_mount VERIFIED para ese usuario y monto
        if transaction_type == TransactionType.DEPOSIT and not id_verify_mount:
            verify_mount = self.db.exec(
                select(VerifyMount)
                .where(VerifyMount.id_user == id_user)
                .where(VerifyMount.status == VerifyMountStatus.VERIFIED)
                .where(VerifyMount.amount == amount)
                .order_by(VerifyMount.created_at.desc())
            ).first()
            if not verify_mount:
                raise HTTPException(
                    status_code=404, detail="No verified verify_mount found for this user and amount")
            id_verify_mount = verify_mount.id

        # Crear la transacción
        transaction = DriverTransaction(
            id_payment=id_payment,
            id_user=id_user,
            transaction_type=transaction_type,
            amount=amount,
            discount_amount=discount_amount,
            description=description or "",
            reference_id=reference_id,
            id_verify_mount=id_verify_mount,
            transaction_date=transaction_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Actualizar balances según el tipo de transacción
        self._update_balances(transaction, payment)

        # Guardar la transacción
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def _update_balances(self, transaction: DriverTransaction, payment: DriverPayment):
        """Actualiza los balances según el tipo de transacción."""
        if transaction.transaction_type == TransactionType.DEPOSIT:
            # Verificar que existe una verificación de monto
            verify_mount = self.db.get(
                VerifyMount, transaction.id_verify_mount)
            if not verify_mount:
                raise HTTPException(
                    status_code=404, detail="Verify mount not found")
            if verify_mount.status != VerifyMountStatus.VERIFIED:
                raise HTTPException(
                    status_code=400, detail="Mount not verified")

            # Recarga: suma a ambos saldos
            payment.available_balance += transaction.amount
            payment.withdrawable_balance += transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        elif transaction.transaction_type == TransactionType.WITHDRAWAL:
            if payment.withdrawable_balance < transaction.amount or payment.available_balance < transaction.amount:
                raise HTTPException(
                    status_code=400, detail="Insufficient balance")
            payment.withdrawable_balance -= transaction.amount
            payment.available_balance -= transaction.amount
            # La transacción queda en PENDING hasta que se verifique

        elif transaction.transaction_type == TransactionType.SERVICE_PAYMENT:
            if payment.available_balance < transaction.amount:
                raise HTTPException(
                    status_code=400, detail="Insufficient available balance")
            payment.available_balance -= transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        elif transaction.transaction_type == TransactionType.COMMISSION:
            if payment.available_balance < transaction.amount:
                raise HTTPException(
                    status_code=400, detail="Insufficient available balance")
            payment.available_balance -= transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        elif transaction.transaction_type == TransactionType.BONUS:
            # El bono solo suma a available_balance, no a withdrawable_balance
            payment.available_balance += transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        elif transaction.transaction_type == TransactionType.REFUND:
            payment.available_balance += transaction.amount
            payment.withdrawable_balance += transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        elif transaction.transaction_type == TransactionType.ADJUSTMENT:
            # Los ajustes pueden ser positivos o negativos
            payment.available_balance += transaction.amount
            payment.withdrawable_balance += transaction.amount
            transaction.status = TransactionStatus.COMPLETED

        # Al final, total_balance es igual a available_balance (no sumar withdrawable_balance para evitar duplicidad)
        payment.total_balance = payment.available_balance
        payment.updated_at = datetime.utcnow()

    def get_transaction(self, transaction_id: int) -> DriverTransaction:
        """Obtiene una transacción por su ID."""
        transaction = self.db.get(DriverTransaction, transaction_id)
        if not transaction:
            raise HTTPException(
                status_code=404, detail="Transaction not found")
        return transaction

    def get_transactions(
        self,
        user_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DriverTransactionResponse]:
        """Obtiene una lista de transacciones con filtros opcionales."""
        query = select(DriverTransaction)

        if user_id:
            query = query.where(DriverTransaction.id_user == user_id)
        if payment_id:
            query = query.where(DriverTransaction.id_payment == payment_id)
        if transaction_type:
            query = query.where(
                DriverTransaction.transaction_type == transaction_type)
        if status:
            query = query.where(DriverTransaction.status == status)
        if start_date:
            query = query.where(
                DriverTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(DriverTransaction.transaction_date <= end_date)

        query = query.order_by(DriverTransaction.transaction_date.desc())
        query = query.offset(skip).limit(limit)

        transactions = self.db.exec(query).all()

        # Obtener las verificaciones de monto relacionadas
        verify_mount_ids = [
            t.id_verify_mount for t in transactions if t.id_verify_mount]
        verify_mounts = {}
        if verify_mount_ids:
            verify_mount_query = select(VerifyMount).where(
                VerifyMount.id.in_(verify_mount_ids))
            verify_mounts = {vm.id: vm for vm in self.db.exec(
                verify_mount_query).all()}

        return [
            DriverTransactionResponse.from_transaction(
                transaction,
                verify_mounts.get(transaction.id_verify_mount)
            )
            for transaction in transactions
        ]

    def update_transaction(
        self,
        transaction_id: int,
        transaction_data: DriverTransactionUpdate,
        current_user: User
    ) -> DriverTransaction:
        """Actualiza una transacción existente."""
        transaction = self.get_transaction(transaction_id)

        # Solo permitir actualizar ciertos campos
        update_data = transaction_data.dict(exclude_unset=True)

        # Si se está actualizando el estado, verificar permisos y lógica de negocio
        if "status" in update_data:
            if not current_user.is_admin:
                raise HTTPException(
                    status_code=403, detail="Only admins can update transaction status")

            new_status = update_data["status"]
            if transaction.status == TransactionStatus.COMPLETED:
                raise HTTPException(
                    status_code=400, detail="Cannot update completed transaction")

            if new_status == TransactionStatus.COMPLETED:
                # Si se está completando una transacción, actualizar balances
                payment = self.db.get(DriverPayment, transaction.id_payment)
                if not payment:
                    raise HTTPException(
                        status_code=404, detail="Payment not found")

                if transaction.transaction_type == TransactionType.WITHDRAWAL:
                    # Verificar que el balance retirable sigue siendo suficiente
                    if payment.withdrawable_balance < transaction.amount:
                        raise HTTPException(
                            status_code=400, detail="Insufficient withdrawable balance")
                    payment.withdrawable_balance -= transaction.amount
                elif transaction.transaction_type == TransactionType.DEPOSIT:
                    # Verificar que existe una verificación de monto
                    verify_mount = self.db.get(
                        VerifyMount, transaction.id_verify_mount)
                    if not verify_mount:
                        raise HTTPException(
                            status_code=404, detail="Verify mount not found")
                    if verify_mount.status != VerifyMountStatus.VERIFIED:
                        raise HTTPException(
                            status_code=400, detail="Mount not verified")

                    payment.available_balance += transaction.amount
                    payment.withdrawable_balance += transaction.amount

                payment.updated_at = datetime.utcnow()

        # Actualizar la transacción
        for key, value in update_data.items():
            setattr(transaction, key, value)

        transaction.updated_at = datetime.utcnow()

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def get_transaction_summary(
        self,
        user_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Obtiene un resumen de las transacciones con totales por tipo."""
        query = select(DriverTransaction)

        if user_id:
            query = query.where(DriverTransaction.id_user == user_id)
        if payment_id:
            query = query.where(DriverTransaction.id_payment == payment_id)
        if start_date:
            query = query.where(
                DriverTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(DriverTransaction.transaction_date <= end_date)

        transactions = self.db.exec(query).all()

        summary = {
            "total_income": Decimal("0"),
            "total_expense": Decimal("0"),
            "by_type": {}
        }

        for transaction in transactions:
            amount = transaction.amount
            movement_type = (
                MovementType.INCOME
                if transaction.transaction_type in [TransactionType.BONUS, TransactionType.DEPOSIT, TransactionType.REFUND]
                else MovementType.EXPENSE
            )

            if movement_type == MovementType.INCOME:
                summary["total_income"] += amount
            else:
                summary["total_expense"] += amount

            # Agrupar por tipo de transacción
            if transaction.transaction_type not in summary["by_type"]:
                summary["by_type"][transaction.transaction_type] = {
                    "count": 0,
                    "total": Decimal("0")
                }

            summary["by_type"][transaction.transaction_type]["count"] += 1
            summary["by_type"][transaction.transaction_type]["total"] += amount

        return summary
