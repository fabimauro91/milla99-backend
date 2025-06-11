import os
import pytest
import sqlalchemy
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from app.main import fastapi_app as app
from app.core.db import get_session
from app.core.init_data import init_data

TEST_DB_NAME = "milla99_test"
MYSQL_ROOT_URL = "mysql+mysqlconnector://root:root@localhost:3306/"


@pytest.fixture(scope="session", autouse=True)
def create_and_drop_test_db():
    # Crear la base de datos
    engine = sqlalchemy.create_engine(MYSQL_ROOT_URL)
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(sqlalchemy.text(f"CREATE DATABASE {TEST_DB_NAME}"))
    # Cambiar la variable de entorno para que los tests usen la nueva DB
    os.environ[
        "DATABASE_URL"] = f"mysql+mysqlconnector://root:root@localhost:3306/{TEST_DB_NAME}"
    yield
    # Eliminar la base de datos al finalizar los tests
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(
            f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))


# Forzar uso de MySQL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith("mysql"):
    raise RuntimeError(
        "Debes definir la variable de entorno DATABASE_URL con un DSN de MySQL para correr los tests.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


@pytest.fixture(scope="session", autouse=True)
def setup_db_data():
    SQLModel.metadata.create_all(engine)
    init_data()  # Pobla la base de datos con datos mínimos y de ejemplo
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture():
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
