from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles

from .core.db import create_all_tables
from .routers import users, drivers, auth
from .routers import  users, drivers, auth, verify_docs
from .core.config import settings
from .core.init_data import init_data
from .core.middleware.auth import JWTAuthMiddleware



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

app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    description="Una API simple creada con FastAPI",
    version=settings.APP_VERSION
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# Agregar middleware de autenticación
app.add_middleware(JWTAuthMiddleware)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(drivers.router)
app.include_router(verify_docs.router)