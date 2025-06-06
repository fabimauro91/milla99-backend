from sqlmodel import Session
from app.models.user import User


def check_and_notify_low_balance(session: Session, user_id: int, balance: int):
    """
    Verifica si el saldo está bajo el umbral y envía una notificación por WhatsApp.
    Por ahora solo imprime el mensaje, pero en producción se reemplazará por la llamada real a la API de WhatsApp.

    Args:
        session: Sesión de base de datos
        user_id: ID del usuario
        balance: Saldo actual del usuario
    """
    if balance <= 10000:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            message = (
                f"Hola {user.full_name}, tu saldo ha bajado a {balance} pesos. "
                "Recarga para poder seguir usando el servicio."
            )
            # En producción, reemplazar este print por la llamada real a tu API de WhatsApp.
            print(
                f"[WHATSAPP] Enviando a {user.country_code}{user.phone_number}: {message}")
