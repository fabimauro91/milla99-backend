from hashids import Hashids

# Cambia este salt por uno seguro y único para tu proyecto
HASHIDS_SALT = "tu_salt_secreto_unico"
HASHIDS_MIN_LENGTH = 6

hashids = Hashids(salt=HASHIDS_SALT, min_length=HASHIDS_MIN_LENGTH)

def encode_id(id_real: int) -> str:
    """Convierte un ID numérico en un hashid seguro para exponer en URLs o APIs."""
    return hashids.encode(id_real)

def decode_id(hashid: str) -> int:
    """Convierte un hashid recibido en la API al ID numérico real. Lanza ValueError si no es válido."""
    decoded = hashids.decode(hashid)
    if not decoded:
        raise ValueError("Hashid inválido o no decodificable")
    return decoded[0] 