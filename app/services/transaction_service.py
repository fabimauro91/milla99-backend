from sqlmodel import Session, select
from app.models.transaction import Transaction, TransactionType
from app.models.verify_mount import VerifyMount
from sqlalchemy import func
from fastapi import HTTPException
from uuid import UUID
from app.models.user import User
from app.utils.balance_notifications import check_and_notify_low_balance


class TransactionService:
    def __init__(self, session):
        self.session = session

    def create_transaction(self, user_id: UUID, income=0, expense=0, type=None, client_request_id=None, description=None):
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()

        # Validación para RECHARGE
        if type == TransactionType.RECHARGE or type == TransactionType.PENALITY_COMPENSATION:
            if income <= 0 or expense != 0:
                raise HTTPException(
                    status_code=400,
                    detail="Las transacciones de tipo RECHARGE solo pueden ser ingresos (income > 0, expense == 0)."
                )
            if verify_mount:
                verify_mount.mount += income
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                verify_mount = VerifyMount(user_id=user_id, mount=income)
                self.session.add(verify_mount)
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)

        # Validación para WITHDRAWAL
        elif type == TransactionType.WITHDRAWAL:
            if income != 0 or expense <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Las transacciones de tipo WITHDRAWAL solo pueden ser egresos (income == 0, expense > 0)."
                )
            if not verify_mount or verify_mount.mount < expense:
                raise HTTPException(
                    status_code=400,
                    detail="Saldo insuficiente para realizar el retiro."
                )
            verify_mount.mount -= expense
            check_and_notify_low_balance(
                self.session, user_id, verify_mount.mount)

        # Permitir egresos para SERVICE
        elif type == TransactionType.SERVICE or type == TransactionType.PENALITY_DEDUCTION:
            if not verify_mount or verify_mount.mount < expense:
                raise HTTPException(
                    status_code=400,
                    detail="Saldo insuficiente para realizar la transacción."
                )
            verify_mount.mount -= expense
            check_and_notify_low_balance(
                self.session, user_id, verify_mount.mount)

        # Validación para SERVICE (solo ingresos)
        elif type == TransactionType.SERVICE:
            if income <= 0 or expense != 0:
                raise HTTPException(
                    status_code=400,
                    detail="Las transacciones de tipo SERVICE solo pueden ser ingresos (income > 0, expense == 0)."
                )
            if verify_mount:
                verify_mount.mount += income
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                verify_mount = VerifyMount(user_id=user_id, mount=income)
                self.session.add(verify_mount)
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)

        # Otros tipos (por defecto solo ingresos)
        elif type != TransactionType.BONUS:
            if income <= 0 or expense != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Las transacciones de tipo {type} solo pueden ser ingresos (income > 0, expense == 0)."
                )
            if verify_mount:
                verify_mount.mount += income
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                verify_mount = VerifyMount(user_id=user_id, mount=income)
                self.session.add(verify_mount)
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)

        transaction = Transaction(
            user_id=user_id,
            income=income,
            expense=expense,
            type=type,
            client_request_id=client_request_id,
            description=description
        )
        self.session.add(transaction)
        # No commit aquí
        if type != TransactionType.BONUS:
            return {
                "message": "Transacción exitosa",
                "amount": verify_mount.mount,
                "transaction_type": type
            }
        else:
            valor = income if income else expense
            return {
                "message": "Transacción exitosa",
                "amount": valor,
                "transaction_type": type
            }

    def get_user_balance(self, user_id: UUID):
        total_income = self.session.query(func.sum(Transaction.income)).filter(
            Transaction.user_id == user_id).scalar() or 0
        total_expense = self.session.query(func.sum(Transaction.expense)).filter(
            Transaction.user_id == user_id).scalar() or 0
        withdrawable_income = self.session.query(func.sum(Transaction.income)).filter(
            Transaction.user_id == user_id, Transaction.type != TransactionType.BONUS).scalar() or 0
        available = total_income - total_expense
        withdrawable = withdrawable_income - total_expense
        withdrawable = max(withdrawable, 0)
        if total_income == withdrawable_income:
            withdrawable = available
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()
        mount = verify_mount.mount if verify_mount else 0
        return {
            "available": available,
            "withdrawable": withdrawable,
            "mount": mount
        }

    def list_transactions(self, user_id: UUID):
        return self.session.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date.desc()).all()
