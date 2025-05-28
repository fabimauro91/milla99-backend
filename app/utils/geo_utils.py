from geoalchemy2.shape import to_shape

def wkb_to_coords(wkb):
    """
    Convierte un campo WKBElement a un diccionario con latitud y longitud.
    Args:
        wkb: WKBElement de la base de datos
    Returns:
        dict con 'lat' y 'lng' o None si wkb es None
    """
    if wkb is None:
        return None
    point = to_shape(wkb)
    return {"lat": point.y, "lng": point.x} 