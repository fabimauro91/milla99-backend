from sqlmodel import Session
from app.models.transaction import Transaction, TransactionType
from app.models.verify_mount import VerifyMount
from datetime import datetime, date
from fastapi import HTTPException
from uuid import UUID

# Constantes
WITHDRAWAL_MONTHLY_LIMIT = 3
WITHDRAWAL_COMMISSION = 3000


class InsufficientFundsException(Exception):
    pass


def assert_can_withdraw(session: Session, user_id: UUID, amount: int):
    """
    Verifica si el usuario puede realizar un retiro.
    Valida que tenga saldo suficiente.
    """
    verify_mount = session.query(VerifyMount).filter(
        VerifyMount.user_id == user_id).first()
    if not verify_mount or verify_mount.mount < amount:
        raise InsufficientFundsException()


def get_monthly_confirmed_withdrawals(session: Session, user_id: UUID) -> int:
    """
    Cuenta los retiros confirmados del usuario en el mes actual.
    Solo cuenta las transacciones de tipo WITHDRAWAL que están confirmadas.

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario

    Returns:
        int: Número de retiros confirmados en el mes actual
    """
    # Obtener el primer día del mes actual
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)

    # Contar transacciones de retiro confirmadas en el mes actual
    count = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.WITHDRAWAL,
        Transaction.is_confirmed == True,
        Transaction.date >= first_day_of_month
    ).count()

    return count


def calculate_withdrawal_amount(amount: int, confirmed_withdrawals: int) -> tuple[int, int]:
    """
    Calcula el monto total a retirar incluyendo comisión si aplica.

    Args:
        amount: Monto base a retirar
        confirmed_withdrawals: Número de retiros confirmados en el mes

    Returns:
        tuple[int, int]: (monto_total, comisión)
    """
    commission = WITHDRAWAL_COMMISSION if confirmed_withdrawals >= WITHDRAWAL_MONTHLY_LIMIT else 0
    total_amount = amount + commission
    return total_amount, commission
