from sqlmodel import Session, select
from app.models.transaction import Transaction, TransactionType
from app.models.verify_mount import VerifyMount
from sqlalchemy import func
from fastapi import HTTPException
import traceback
from uuid import UUID
from app.models.user import User
from app.utils.balance_notifications import check_and_notify_low_balance


class TransactionService:
    def __init__(self, session):
        self.session = session

    def create_transaction(self, user_id: UUID, income=0, expense=0, type=None, client_request_id=None):
        print("TRACEBACK INICIO:\n", "".join(traceback.format_stack()))
        print(f"DEBUG income: {income}, expense: {expense}, type: {type}")

        # Validación de tipo y monto
        if type == TransactionType.RECHARGE:
            if income <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Las transacciones de tipo {type} solo pueden ser ingresos (income > 0, expense == 0)."
                )

        # Validar saldo suficiente para egresos
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()

        if expense > 0 and type != TransactionType.BONUS:
            if not verify_mount or verify_mount.mount < expense:
                raise HTTPException(
                    status_code=400,
                    detail="Saldo insuficiente para realizar la transacción."
                )

        transaction = Transaction(
            user_id=user_id,
            income=income,
            expense=expense,
            type=type,
            client_request_id=client_request_id
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)

        # Actualizar el mount en VerifyMount para ingresos y egresos
        print(
            f"DEBUG verify_mount antes: {verify_mount.mount if verify_mount else 'NO EXISTE'}")

        if type == TransactionType.RECHARGE:
            if verify_mount:
                verify_mount.mount += income
                self.session.commit()
                # Verificar saldo bajo después de actualizar
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                verify_mount = VerifyMount(user_id=user_id, mount=income)
                self.session.add(verify_mount)
                self.session.commit()
                # Verificar saldo bajo después de crear
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
                print("DEBUG verify_mount creado")
        elif type == TransactionType.SERVICE or type == TransactionType.WITHDRAW:
            if verify_mount:
                verify_mount.mount -= expense
                self.session.commit()
                # Verificar saldo bajo después de actualizar
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="El conductor no tiene saldo."
                )
        elif type != TransactionType.BONUS:
            if verify_mount:
                verify_mount.mount += income
                self.session.commit()
                # Verificar saldo bajo después de actualizar
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
            else:
                verify_mount = VerifyMount(user_id=user_id, mount=income)
                self.session.add(verify_mount)
                self.session.commit()
                # Verificar saldo bajo después de crear
                check_and_notify_low_balance(
                    self.session, user_id, verify_mount.mount)
                print("DEBUG verify_mount creado")

        if type != TransactionType.BONUS:
            return {
                "message": "Transacción exitosa",
                "amount": verify_mount.mount,
                "transaction_type": type
            }
        else:
            if income:
                valor = income
            else:
                valor = expense
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
