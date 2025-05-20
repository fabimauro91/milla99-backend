from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from app.models.driver_transaction import (
    DriverTransaction, DriverTransactionCreate,
    DriverTransactionUpdate, TransactionType
)
from app.models.driver_payment import PaymentStatus
from app.services.driver_payment_service import DriverPaymentService


class DriverTransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.payment_service = DriverPaymentService(db)

    def create_transaction(self, transaction: DriverTransactionCreate) -> Optional[DriverTransaction]:
        """Crear una nueva transacción y actualizar los balances correspondientes"""
        # Verificar que existe la cuenta de pago
        payment = self.payment_service.get_payment_by_id(
            transaction.id_payment)
        if not payment:
            return None

        # Crear la transacción
        db_transaction = DriverTransaction(**transaction.model_dump())
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)

        # Actualizar los balances según el tipo de transacción
        net_amount = transaction.amount - transaction.discount_amount

        if transaction.transaction_type == TransactionType.DEPOSIT:
            # Para depósitos, el monto va a pending_balance inicialmente
            self.payment_service.update_balances(
                payment_id=transaction.id_payment,
                total_change=net_amount,
                pending_change=net_amount
            )
        elif transaction.transaction_type == TransactionType.WITHDRAWAL:
            # Para retiros, se reduce el available_balance
            self.payment_service.update_balances(
                payment_id=transaction.id_payment,
                available_change=-net_amount
            )
        elif transaction.transaction_type == TransactionType.COMMISSION:
            # Para comisiones, se reduce el available_balance
            self.payment_service.update_balances(
                payment_id=transaction.id_payment,
                available_change=-net_amount
            )
        elif transaction.transaction_type == TransactionType.REFUND:
            # Para reembolsos, se aumenta el available_balance
            self.payment_service.update_balances(
                payment_id=transaction.id_payment,
                available_change=net_amount
            )

        return db_transaction

    def get_transaction_by_id(self, transaction_id: int) -> Optional[DriverTransaction]:
        """Obtener una transacción por su ID"""
        return self.db.get(DriverTransaction, transaction_id)

    def get_transactions_by_payment_id(self, payment_id: int) -> List[DriverTransaction]:
        """Obtener todas las transacciones de una cuenta de pago"""
        statement = select(DriverTransaction).where(
            DriverTransaction.id_payment == payment_id)
        return list(self.db.exec(statement))

    def get_transactions_by_user_id(self, user_id: int) -> List[DriverTransaction]:
        """Obtener todas las transacciones de un usuario"""
        statement = select(DriverTransaction).where(
            DriverTransaction.id_user == user_id)
        return list(self.db.exec(statement))

    def update_transaction_status(self, transaction_id: int, new_status: PaymentStatus) -> Optional[DriverTransaction]:
        """Actualizar el estado de una transacción"""
        db_transaction = self.get_transaction_by_id(transaction_id)
        if not db_transaction:
            return None

        # Si la transacción pasa a COMPLETED y es un DEPOSIT, mover de pending a available
        if (new_status == PaymentStatus.COMPLETED and
            db_transaction.status == PaymentStatus.PENDING and
                db_transaction.transaction_type == TransactionType.DEPOSIT):

            net_amount = db_transaction.amount - db_transaction.discount_amount
            self.payment_service.update_balances(
                payment_id=db_transaction.id_payment,
                pending_change=-net_amount,
                available_change=net_amount
            )

        db_transaction.status = new_status
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction

    def get_all_transactions(self) -> List[DriverTransaction]:
        """Obtener todas las transacciones"""
        statement = select(DriverTransaction)
        return list(self.db.exec(statement))

    def delete_transaction(self, transaction_id: int) -> bool:
        """Eliminar una transacción (solo para administradores)"""
        db_transaction = self.get_transaction_by_id(transaction_id)
        if not db_transaction:
            return False

        # Revertir los cambios en los balances
        net_amount = db_transaction.amount - db_transaction.discount_amount

        if db_transaction.transaction_type == TransactionType.DEPOSIT:
            if db_transaction.status == PaymentStatus.COMPLETED:
                self.payment_service.update_balances(
                    payment_id=db_transaction.id_payment,
                    total_change=-net_amount,
                    available_change=-net_amount
                )
            else:
                self.payment_service.update_balances(
                    payment_id=db_transaction.id_payment,
                    total_change=-net_amount,
                    pending_change=-net_amount
                )
        elif db_transaction.transaction_type == TransactionType.WITHDRAWAL:
            self.payment_service.update_balances(
                payment_id=db_transaction.id_payment,
                available_change=net_amount
            )
        elif db_transaction.transaction_type == TransactionType.COMMISSION:
            self.payment_service.update_balances(
                payment_id=db_transaction.id_payment,
                available_change=net_amount
            )
        elif db_transaction.transaction_type == TransactionType.REFUND:
            self.payment_service.update_balances(
                payment_id=db_transaction.id_payment,
                available_change=-net_amount
            )

        self.db.delete(db_transaction)
        self.db.commit()
        return True
