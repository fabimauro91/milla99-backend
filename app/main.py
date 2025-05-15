from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles

from .core.db import create_all_tables
from .routers import users, drivers, auth
from .routers import users, drivers, auth, verify_docs, client_request, driver_position
from .core.config import settings
from .core.init_data import init_data
from .core.middleware.auth import JWTAuthMiddleware
from .core.sio_events import sio
import socketio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que se ejecuta al iniciar la aplicación
    import secrets
    print(secrets.token_hex(32))
    print("Iniciando la aplicación...")
    # Crear las tablas
    for _ in create_all_tables(app):
        pass
    init_data()  # Inicializar todos los datos por defecto
    yield
    # Código que se ejecuta al cerrar la aplicación
    print("Cerrando la aplicación...")

fastapi_app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    description="Una API simple creada con FastAPI",
    version=settings.APP_VERSION
)

# Configuración CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

# Agregar middleware de autenticación
fastapi_app.add_middleware(JWTAuthMiddleware)

# Agregar routers
fastapi_app.include_router(users.router)
fastapi_app.include_router(auth.router)
fastapi_app.include_router(drivers.router)
fastapi_app.include_router(verify_docs.router)
fastapi_app.include_router(client_request.router)
fastapi_app.include_router(driver_position.router)

# Socket.IO debe ser lo último
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
