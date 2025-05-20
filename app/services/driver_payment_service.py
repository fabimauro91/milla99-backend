from sqlmodel import Session, select
from typing import List, Optional
from decimal import Decimal
from app.models.driver_payment import DriverPayment, DriverPaymentCreate, DriverPaymentUpdate, PaymentStatus
from app.models.user import User


class DriverPaymentService:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, payment: DriverPaymentCreate) -> DriverPayment:
        """Crear una nueva cuenta de pago para un conductor"""
        db_payment = DriverPayment(**payment.model_dump())
        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def get_payment_by_user_id(self, user_id: int) -> Optional[DriverPayment]:
        """Obtener la cuenta de pago de un conductor por su ID"""
        statement = select(DriverPayment).where(
            DriverPayment.id_user == user_id)
        return self.db.exec(statement).first()

    def get_payment_by_id(self, payment_id: int) -> Optional[DriverPayment]:
        """Obtener una cuenta de pago por su ID"""
        return self.db.get(DriverPayment, payment_id)

    def update_payment(self, payment_id: int, payment_update: DriverPaymentUpdate) -> Optional[DriverPayment]:
        """Actualizar una cuenta de pago"""
        db_payment = self.get_payment_by_id(payment_id)
        if not db_payment:
            return None

        update_data = payment_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_payment, key, value)

        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

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
