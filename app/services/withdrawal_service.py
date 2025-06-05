from sqlmodel import Session, select
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.models.transaction import Transaction, TransactionType
from app.utils.withdrawal_utils import assert_can_withdraw, InsufficientFundsException
from app.models.verify_mount import VerifyMount
from app.models.bank_account import BankAccount
from fastapi import HTTPException
from app.utils.balance_notifications import check_and_notify_low_balance
from uuid import UUID


class WithdrawalService:
    def __init__(self, session: Session):
        self.session = session

    def validate_bank_account(self, user_id: UUID, bank_account_id: UUID) -> BankAccount:
        """
        Valida que la cuenta bancaria exista y pertenezca al usuario.
        """
        bank_account = self.session.get(BankAccount, bank_account_id)
        if not bank_account:
            raise HTTPException(
                status_code=404, detail="Bank account not found")
        if bank_account.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Bank account does not belong to user")
        if not bank_account.is_active:
            raise HTTPException(
                status_code=400, detail="Bank account is not active")
        return bank_account

    def request_withdrawal(self, user_id: UUID, amount: int, bank_account_id: UUID):
        """
        Solicita un retiro:
        1. Verifica el saldo
        2. Verifica la cuenta bancaria
        3. Descuenta el monto inmediatamente
        4. Crea la transacción con is_confirmed=True
        5. Crea el retiro en estado PENDING asociado a la cuenta bancaria
        """
        # Verificar saldo suficiente
        try:
            assert_can_withdraw(self.session, user_id, amount)
        except InsufficientFundsException:
            raise HTTPException(
                status_code=400, detail="Insufficient funds for withdrawal")

        # Verificar cuenta bancaria
        bank_account = self.validate_bank_account(user_id, bank_account_id)

        # Descontar saldo inmediatamente
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == user_id).first()
        if verify_mount:
            verify_mount.mount -= amount
            self.session.add(verify_mount)
            # Verificar saldo bajo usando la función utilitaria
            check_and_notify_low_balance(
                self.session, user_id, verify_mount.mount)

        # Crear el retiro en estado pending
        withdrawal = Withdrawal(
            user_id=user_id,
            amount=amount,
            status=WithdrawalStatus.PENDING,
            bank_account_id=bank_account_id
        )
        self.session.add(withdrawal)
        self.session.flush()  # Para obtener el ID del withdrawal

        # Crear transacción de egreso
        transaction = Transaction(
            user_id=user_id,
            expense=amount,
            type=TransactionType.WITHDRAWAL,
            id_withdrawal=withdrawal.id,
            is_confirmed=True
        )
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(withdrawal)
        return withdrawal

    def approve_withdrawal(self, withdrawal_id: int):
        """
        Aprueba un retiro:
        1. Solo cambia el estado a APPROVED
        2. La transacción ya existe y está confirmada
        3. El saldo ya fue descontado al solicitar
        """
        withdrawal = self.session.get(Withdrawal, withdrawal_id)
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")
        if withdrawal.status != WithdrawalStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Withdrawal is not pending")

        # Solo cambiar estado
        withdrawal.status = WithdrawalStatus.APPROVED
        self.session.add(withdrawal)
        self.session.commit()
        return {"message": "Withdrawal approved."}

    def reject_withdrawal(self, withdrawal_id: int):
        """
        Rechaza un retiro:
        1. Cambia el estado a REJECTED
        2. Devuelve el saldo al usuario
        3. Marca la transacción como no confirmada
        """
        withdrawal = self.session.get(Withdrawal, withdrawal_id)
        if not withdrawal:
            raise HTTPException(status_code=404, detail="Withdrawal not found")
        if withdrawal.status != WithdrawalStatus.PENDING:
            raise HTTPException(
                status_code=400, detail="Withdrawal is not pending")

        # Devolver el saldo
        verify_mount = self.session.query(VerifyMount).filter(
            VerifyMount.user_id == withdrawal.user_id).first()
        if verify_mount:
            verify_mount.mount += withdrawal.amount
            self.session.add(verify_mount)

        # Marcar transacción como no confirmada
        transaction = self.session.query(Transaction).filter(
            Transaction.id_withdrawal == withdrawal.id).first()
        if transaction:
            transaction.is_confirmed = False
            self.session.add(transaction)

        # Cambiar estado del retiro
        withdrawal.status = WithdrawalStatus.REJECTED
        self.session.add(withdrawal)
        self.session.commit()
        return {"message": "Withdrawal rejected and funds returned."}
