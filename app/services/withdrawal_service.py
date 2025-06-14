from sqlmodel import Session, select
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.models.transaction import Transaction, TransactionType
from app.utils.withdrawal_utils import (
    assert_can_withdraw,
    get_monthly_confirmed_withdrawals,
    calculate_withdrawal_amount,
    InsufficientFundsException,
    WITHDRAWAL_MONTHLY_LIMIT,
    WITHDRAWAL_COMMISSION
)
from app.models.verify_mount import VerifyMount
from app.models.bank_account import BankAccount
from fastapi import HTTPException
from app.utils.balance_notifications import check_and_notify_low_balance
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import joinedload


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

    def request_withdrawal(
        self,
        user_id: UUID,
        amount: int,
        bank_account_id: UUID,
        description: Optional[str] = None
    ) -> Withdrawal:
        """
        Procesa una solicitud de retiro.

        Args:
            user_id: ID del usuario que solicita el retiro
            amount: Monto base a retirar
            bank_account_id: ID de la cuenta bancaria
            description: Descripción opcional del retiro

        Returns:
            Withdrawal: El registro de retiro creado

        Raises:
            HTTPException: Si hay algún error en el proceso
        """
        try:
            # Verificar que la cuenta bancaria existe y pertenece al usuario
            bank_account = self.session.query(BankAccount).filter(
                BankAccount.id == bank_account_id,
                BankAccount.user_id == user_id
            ).first()

            if not bank_account:
                raise HTTPException(
                    status_code=404,
                    detail="Bank account not found or does not belong to user"
                )

            # Obtener el número de retiros confirmados del mes
            confirmed_withdrawals = get_monthly_confirmed_withdrawals(
                self.session, user_id)

            # Calcular el monto total incluyendo comisión si aplica
            total_amount, commission = calculate_withdrawal_amount(
                amount, confirmed_withdrawals)

            # Verificar saldo suficiente para el monto total
            assert_can_withdraw(self.session, user_id, total_amount)

            # Crear el registro de retiro con el monto total
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=total_amount,  # Monto total (base + comisión)
                status=WithdrawalStatus.PENDING,
                bank_account_id=bank_account_id,
                withdrawal_date=datetime.utcnow()
            )
            self.session.add(withdrawal)
            self.session.flush()

            # Crear la transacción de retiro
            transaction = Transaction(
                user_id=user_id,
                type=TransactionType.WITHDRAWAL,
                expense=total_amount,
                description=(
                    f"Retiro a cuenta bancaria {bank_account.account_number}" +
                    (f" (incluye comisión de {commission})" if commission > 0 else "")
                ),
                bank_account_id=bank_account_id,
                id_withdrawal=withdrawal.id,
                is_confirmed=True,
                commission=commission
            )

            # Actualizar el saldo del usuario
            verify_mount = self.session.query(VerifyMount).filter(
                VerifyMount.user_id == user_id
            ).first()

            verify_mount.mount -= total_amount
            verify_mount.updated_at = datetime.utcnow()

            # Guardar los cambios
            self.session.add(transaction)
            self.session.commit()
            self.session.refresh(withdrawal)

            return withdrawal

        except InsufficientFundsException:
            raise HTTPException(
                status_code=400,
                detail="Insufficient funds for withdrawal"
            )
        except Exception as e:
            self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error processing withdrawal: {str(e)}"
            )

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

    def reject_withdrawal(self, withdrawal_id: UUID) -> dict:
        """
        Rechaza un retiro y devuelve el monto total al usuario.
        """
        withdrawal = self.session.query(Withdrawal).filter(
            Withdrawal.id == withdrawal_id,
            Withdrawal.status == WithdrawalStatus.PENDING
        ).first()

        if not withdrawal:
            raise HTTPException(
                status_code=404,
                detail="Withdrawal not found or not in pending status"
            )

        try:
            # Buscar la transacción original asociada al retiro
            original_transaction = self.session.query(Transaction).filter(
                Transaction.id_withdrawal == withdrawal.id,
                Transaction.type == TransactionType.WITHDRAWAL
            ).first()

            if not original_transaction:
                raise HTTPException(
                    status_code=404,
                    detail="Original withdrawal transaction not found"
                )

            # Marcar la transacción como no confirmada
            original_transaction.is_confirmed = False

            # Actualizar el estado del retiro
            withdrawal.status = WithdrawalStatus.REJECTED

            # Devolver el monto al usuario
            verify_mount = self.session.query(VerifyMount).filter(
                VerifyMount.user_id == withdrawal.user_id
            ).first()

            verify_mount.mount += withdrawal.amount
            verify_mount.updated_at = datetime.utcnow()

            self.session.commit()

            return {
                "message": "Withdrawal rejected and funds returned.",
            }

        except Exception as e:
            self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error rejecting withdrawal: {str(e)}"
            )

    def list_withdrawals(
        self,
        status: Optional[WithdrawalStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Withdrawal]:
        """
        Lista los retiros con opción de filtrar por status.

        Args:
            status: Status opcional para filtrar los retiros
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar

        Returns:
            List[Withdrawal]: Lista de retiros con información relacionada
        """
        query = select(Withdrawal).options(
            joinedload(Withdrawal.user),
            joinedload(Withdrawal.bank_account)
        ).order_by(Withdrawal.withdrawal_date.desc())

        if status:
            query = query.where(Withdrawal.status == status)

        return self.session.exec(query.offset(skip).limit(limit)).all()
