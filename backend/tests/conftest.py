import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import Base, get_db
from app.db import models
from app.core import security
from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(auth_router, prefix="/auth")
    app.include_router(incidents_router, prefix="/incidents")
    app.dependency_overrides[get_db] = override_get_db

    db = SessionLocal()
    yield app, SessionLocal
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    app, _ = db_session
    return TestClient(app)


@pytest.fixture
def session(db_session):
    _, SessionLocal = db_session
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def user_factory(session):
    def _make(email="devops@example.com", password="secreto123", name="DevOps", active=True):
        user = models.User(
            email=email,
            name=name,
            hashed_password=security.get_password_hash(password),
            is_active=active,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _make


@pytest.fixture
def access_token(user_factory):
    user = user_factory()
    return security.create_access_token(subject=user.id)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
