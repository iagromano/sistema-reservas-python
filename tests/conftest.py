import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Importamos la app y la función de la que depende la sesión en api.py
from api import app, obtener_sesion

# Configuración de SQLite en memoria compartida para los tests
DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    """Crea las tablas antes de cada test y las elimina al finalizar."""
    SQLModel.metadata.create_engine = engine
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Sobrescribe la dependencia 'obtener_sesion' de FastAPI por la sesión de prueba."""

    def obtener_sesion_override():
        return session

    app.dependency_overrides[obtener_sesion] = obtener_sesion_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()