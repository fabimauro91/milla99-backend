from sqlmodel import Session, select
from app.models.driver_savings import DriverSavings, SavingsType
from datetime import datetime
from app.models.transaction import Transaction, TransactionType
from app.models.project_settings import ProjectSettings


class DriverSavingsService:
    # Valor por defecto y caché del valor mínimo
    _DEFAULT_MINIMUM_WITHDRAWAL_AMOUNT = 50000
    _minimum_withdrawal_amount = _DEFAULT_MINIMUM_WITHDRAWAL_AMOUNT

    def __init__(self, session: Session):
        self.session = session
        # Actualizar el valor mínimo al inicializar el servicio
        self._update_minimum_withdrawal_amount()

    def _get_current_minimum_amount(self) -> int:
        """Obtiene el valor mínimo actual desde la base de datos"""
        try:
            settings = self.session.exec(select(ProjectSettings)).first()
            if settings and settings.amount:
                return int(settings.amount)
        except Exception:
            pass
        return self._DEFAULT_MINIMUM_WITHDRAWAL_AMOUNT

    def _update_minimum_withdrawal_amount(self):
        """Actualiza el valor mínimo de retiro desde ProjectSettings"""
        self._minimum_withdrawal_amount = self._get_current_minimum_amount()

    @classmethod
    def get_minimum_withdrawal_amount(cls) -> int:
        """Obtiene el valor mínimo actual para retiro"""
        return cls._minimum_withdrawal_amount

    def get_driver_savings_status(self, user_id: int):
        # Verificar el valor actual en cada operación
        min_amount = self._get_current_minimum_amount()
        self._minimum_withdrawal_amount = min_amount  # Actualizar el caché

        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings:
            return {
                "mount": 0,
                "status": "SAVING",
                "can_withdraw": False,
                "message": "No savings yet."
            }

        can_withdraw = savings.mount >= min_amount
        return {
            "mount": savings.mount,
            "status": savings.status,
            "can_withdraw": can_withdraw,
            "message": f"You can withdraw your savings (minimum {min_amount})." if can_withdraw else f"You need at least {min_amount} to withdraw."
        }

    def withdraw_savings(self, user_id: int):
        # Verificar el valor actual en cada operación
        min_amount = self._get_current_minimum_amount()
        self._minimum_withdrawal_amount = min_amount  # Actualizar el caché

        savings = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not savings or savings.mount == 0:
            return {"success": False, "message": "No savings to withdraw."}

        if savings.mount < min_amount:
            return {
                "success": False,
                "message": f"You need at least {min_amount} to withdraw. Current balance: {savings.mount}"
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
