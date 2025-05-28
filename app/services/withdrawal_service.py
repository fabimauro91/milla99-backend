from sqlmodel import Session, select
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.models.transaction import Transaction, TransactionType
from app.utils.withdrawal_utils import assert_can_withdraw, InsufficientFundsException
from app.models.verify_mount import VerifyMount
from fastapi import HTTPException


class WithdrawalService:
    def __init__(self, session: Session):
        self.session = session

    def approve_withdrawal(self, withdrawal_id: int):
        withdrawal = self.session.get(Withdrawal, withdrawal_id)
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")
        if withdrawal.status != WithdrawalStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Withdrawal is not pending")
        # Verificar saldo antes de aprobar
        try:
            assert_can_withdraw(
                self.session, withdrawal.user_id, withdrawal.amount)
        except InsufficientFundsException:
            raise HTTPException(
                status_code=400, detail="Insufficient funds for withdrawal")
        # Crear transacción de egreso
        transaction = Transaction(
            user_id=withdrawal.user_id,
            expense=withdrawal.amount,
            # O crea un nuevo tipo para withdrawals si lo prefieres
            type=TransactionType.SERVICE,
            id_withdrawal=withdrawal.id,
            is_confirmed=True
        )
        self.session.add(transaction)
        # Actualizar saldo en VerifyMount
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == withdrawal.user_id).first()
        if verify_mount:
            verify_mount.mount -= withdrawal.amount
            self.session.add(verify_mount)
        # Cambiar estado del retiro
        withdrawal.status = WithdrawalStatus.APPROVED
        self.session.add(withdrawal)
        self.session.commit()
        return {"message": "Withdrawal approved and processed."}

    def reject_withdrawal(self, withdrawal_id: int):
        withdrawal = self.session.get(Withdrawal, withdrawal_id)
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")
        if withdrawal.status != WithdrawalStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Withdrawal is not pending")
        # Cambiar estado del retiro
        withdrawal.status = WithdrawalStatus.REJECTED
        self.session.add(withdrawal)
        # Si existe una transacción asociada, marcarla como no confirmada
        transaction = self.session.query(Transaction).filter(
            Transaction.id_withdrawal == withdrawal.id).first()
        if transaction:
            transaction.is_confirmed = False
            self.session.add(transaction)
        self.session.commit()
        return {"message": "Withdrawal rejected."}
