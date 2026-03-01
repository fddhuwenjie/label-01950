import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import database
from app.core.database import Base
from app.entities import completion_entity, dialect_entity, workspace_entity
from app.main import create_app


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session")
def client(test_engine):
    database.engine = test_engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    app = create_app()
    return TestClient(app)
