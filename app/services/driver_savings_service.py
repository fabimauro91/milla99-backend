from sqlmodel import Session
from app.models.driver_savings import DriverSavings, SavingsType
from datetime import datetime
from app.models.transaction import Transaction, TransactionType


class DriverSavingsService:
    MINIMUM_WITHDRAWAL_AMOUNT = 50000  # Monto mínimo para retiro

    def __init__(self, session: Session):
        self.session = session

    def get_driver_savings_status(self, user_id: int):
        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings:
            return {
                "mount": 0,
                "status": "SAVING",
                "can_withdraw": False,
                "message": "No savings yet."
            }

        can_withdraw = savings.mount >= self.MINIMUM_WITHDRAWAL_AMOUNT
        return {
            "mount": savings.mount,
            "status": savings.status,
            "can_withdraw": can_withdraw,
            "message": f"You can withdraw your savings (minimum {self.MINIMUM_WITHDRAWAL_AMOUNT})." if can_withdraw else f"You need at least {self.MINIMUM_WITHDRAWAL_AMOUNT} to withdraw."
        }

    def withdraw_savings(self, user_id: int):
        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings or savings.mount == 0:
            return {"success": False, "message": "No savings to withdraw."}

        if savings.mount < self.MINIMUM_WITHDRAWAL_AMOUNT:
            return {
                "success": False,
                "message": f"You need at least {self.MINIMUM_WITHDRAWAL_AMOUNT} to withdraw. Current balance: {savings.mount}"
            }

        amount = savings.mount
        # Crear transacción de retiro de ahorro
        transaction = Transaction(
            user_id=user_id,
            income=0,
            expense=amount,
            type=TransactionType.SAVING_BALANCE,
            is_confirmed=True
        )
        self.session.add(transaction)
        # Poner el ahorro en 0 y status en SAVING
        savings.mount = 0
        savings.status = SavingsType.SAVING
        self.session.add(savings)
        self.session.commit()
        return {"success": True, "message": f"Withdrawn {amount} from savings.", "amount": amount}
