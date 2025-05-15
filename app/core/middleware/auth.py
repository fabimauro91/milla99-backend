from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
from app.core.config import settings


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Lista de rutas públicas que no requieren autenticación
        # Formato: (ruta, método_http)
        public_paths = [
            ("/users/", "POST"),
            ("/users/", "GET"),  # Solo el registro de usuarios
            ("/auth/verify/", "POST"),  # Rutas de verificación
            ("/docs", "GET"),  # Documentación
            ("/openapi.json", "GET"),  # Esquema OpenAPI
            ("/drivers/", "POST"),  # Creación de drivers
            ("/openapi.json", "GET"),  # Esquema OpenAPI - AQUÍ FALTABA LA COMA
            ("/verify-docs/","GET"), # Rutas de verify-docs
            ("/verify-docs/","POST"),
            ("/drivers-position/","POST"), # Rutas de drivers-position
            ("/driver-trip-offers/","POST"), # Rutas de driver-trip-offers
            ("/driver-trip-offers/", "GET"), # Rutas de driver-trip-offers
            ("/client-request/distance", "GET"), # Rutas de client-request
            ("/static/uploads/drivers/", "GET"),
            ("/drivers-position/", "POST"),  # Rutas de drivers-position
        ]

        # Verificar si la ruta y método actual están en la lista de públicas
        is_public = any(
            request.url.path.startswith(path) and request.method == method
            for path, method in public_paths
        )

        if is_public:
            return await call_next(request)

        # Para el resto de rutas, verificar token
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "No se proporcionó token de autenticación"}
                )

            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY,
                                 algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")

            if not user_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token inválido"}
                )

            request.state.user_id = int(user_id)

        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token inválido o expirado"}
            )

        return await call_next(request)
