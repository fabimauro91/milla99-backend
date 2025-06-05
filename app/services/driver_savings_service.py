from sqlmodel import Session, select
from app.models.driver_savings import DriverSavings, SavingsType
from datetime import datetime
from app.models.transaction import Transaction, TransactionType
from app.models.project_settings import ProjectSettings
from fastapi import HTTPException
from app.models.user import User
from app.models.user_has_roles import UserHasRole, RoleStatus


class DriverSavingsService:
    # Valor por defecto y caché del valor mínimo
    _DEFAULT_MINIMUM_WITHDRAWAL_AMOUNT = 50000
    _minimum_withdrawal_amount = _DEFAULT_MINIMUM_WITHDRAWAL_AMOUNT

    def __init__(self, session: Session):
        print("DriverSavingsService.__init__: session =", session)
        self.session = session
        from app.services.transaction_service import TransactionService
        self.transaction_service = TransactionService(session)
        print("DriverSavingsService.__init__: self.transaction_service =",
              self.transaction_service)
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

    def transfer_saving_to_balance(self, user_id: str, amount: float):
        # Validar rol DRIVER aprobado
        user_role = self.session.query(UserHasRole).filter(
            UserHasRole.id_user == user_id,
            UserHasRole.id_rol == "DRIVER",
            UserHasRole.status == RoleStatus.APPROVED
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=403, detail="Solo conductores aprobados pueden transferir ahorros.")

        # Validar monto mínimo
        if amount < 50000:
            raise HTTPException(
                status_code=400, detail="El monto mínimo para transferir es 50,000")

        # Obtener DriverSavings
        driver_saving = self.session.query(DriverSavings).filter(
            DriverSavings.user_id == user_id).first()
        if not driver_saving or driver_saving.mount < amount:
            raise HTTPException(
                status_code=400, detail="Saldo insuficiente en el ahorro")

        # Descontar del ahorro
        driver_saving.mount -= amount
        driver_saving.updated_at = datetime.utcnow()
        self.session.add(driver_saving)

        # La transacción (y el "descuento" en la base de datos) ya se registra en create_transaction (que devuelve un diccionario). No se debe agregar (ni committear) de nuevo.
        transaction = self.transaction_service.create_transaction(
            user_id, income=amount, type=TransactionType.TRANSFER_SAVINGS)
        return transaction
