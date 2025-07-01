import pytz
from datetime import datetime

COLOMBIA_TZ = pytz.timezone("America/Bogota")


def utc_to_colombia(dt_utc: datetime) -> datetime:
    """
    Convierte un datetime UTC (naive o aware) a hora de Colombia (aware).
    Si el valor es None, retorna None.
    """
    if dt_utc is None:
        return None
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=pytz.utc)
    return dt_utc.astimezone(COLOMBIA_TZ)
