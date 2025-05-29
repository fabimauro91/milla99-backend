from app.models.verify_mount import VerifyMount


class InsufficientFundsException(Exception):
    pass


def assert_can_withdraw(session, user_id: int, amount: int):
    """
    Lanza una excepción si el usuario no tiene saldo suficiente para el retiro.
    """
    verify_mount = session.query(VerifyMount).filter(
        VerifyMount.user_id == user_id).first()
    if not verify_mount or verify_mount.mount < amount:
        raise InsufficientFundsException("Insufficient funds for withdrawal")
