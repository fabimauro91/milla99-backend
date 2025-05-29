from sqlmodel import Session
from app.models.driver_savings import DriverSavings, SavingsType
from datetime import datetime, timedelta
from app.models.transaction import Transaction, TransactionType


class DriverSavingsService:
    def __init__(self, session: Session):
        self.session = session

    def get_driver_savings_status(self, user_id: int):
        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings:
            return {
                "mount": 0,
                "status": "SAVING",
                "date_saving": None,
                "can_withdraw": False,
                "days_until_withdraw": None,
                "message": "No savings yet."
            }
        # Calcular si ha pasado 1 año desde la primera ganancia
        now = datetime.utcnow()
        date_saving = savings.date_saving
        print(f"NOW: {now}")
        print(f"DATE_SAVING: {date_saving}")
        if date_saving:
            print(f"DAYS UNTIL: {(date_saving - now).days}")
        days_passed = (now - date_saving).days if date_saving else 0
        can_withdraw = days_passed >= 0 and savings.mount > 0 if date_saving else False
        days_until_withdraw = max(
            0, (date_saving - now).days) if savings.mount > 0 and date_saving else None
        return {
            "mount": savings.mount,
            "status": savings.status,
            "date_saving": date_saving,
            "can_withdraw": can_withdraw,
            "days_until_withdraw": days_until_withdraw,
            "message": "You can only withdraw the total accumulated savings." if savings.mount > 0 else "No savings yet."
        }

    def withdraw_savings(self, user_id: int):
        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings or savings.mount == 0:
            return {"success": False, "message": "No savings to withdraw."}
        # Calcular si ha pasado 1 año desde la primera ganancia
        now = datetime.utcnow()
        date_saving = savings.date_saving
        days_passed = (now - date_saving).days
        if days_passed < 365:
            return {"success": False, "message": f"You can only withdraw after 1 year. {365 - days_passed} days left."}
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
        # Poner el ahorro en 0 y status en SAVING, date_saving en None
        savings.mount = 0
        savings.status = SavingsType.SAVING
        savings.date_saving = None
        self.session.add(savings)
        self.session.commit()
        return {"success": True, "message": f"Withdrawn {amount} from savings.", "amount": amount}
