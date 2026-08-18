"""
tests/conftest.py

Shared pytest fixtures for the whole suite.

Uses a fresh in-memory SQLite database per test (fast, zero external
dependencies, no leakage between tests) via a dependency override on
get_db. This project's ORM-to-MySQL compatibility (DDL, cascade deletes,
foreign keys, the Alembic migration) is verified separately against a
real MySQL instance — that verification isn't part of this automated
suite, since it needs a live MySQL server; see the project README's
"Testing against MySQL" section for how to re-run it.

sentence_transformers is stubbed here so the suite never needs to
download model weights or install torch — see app/ai/embedding_model.py's
docstring for why real model inference can't be exercised in this
project's build environment. The stub still produces genuinely different
vectors for different text (a small bag-of-words over a fixed vocabulary),
so tests that check semantic_score varies with content overlap remain
meaningful, not just trivially passing.
"""

import os
import sys
import types

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


def _install_fake_sentence_transformers() -> None:
    if "sentence_transformers" in sys.modules:
        return

    fake_module = types.ModuleType("sentence_transformers")

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, text_or_texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=None):
            vocab = ["python", "fastapi", "postgresql", "docker", "backend", "engineer", "java", "react", "frontend"]

            def vectorize(text: str) -> np.ndarray:
                words = set(text.lower().replace(",", " ").split())
                vec = np.array([1.0 if w in words else 0.0 for w in vocab], dtype=np.float32)
                norm = np.linalg.norm(vec)
                return vec / norm if norm > 0 else vec

            if isinstance(text_or_texts, str):
                return vectorize(text_or_texts)
            return np.stack([vectorize(t) for t in text_or_texts])

    fake_module.SentenceTransformer = FakeSentenceTransformer
    sys.modules["sentence_transformers"] = fake_module


_install_fake_sentence_transformers()

# Test-only settings, applied before any app module is imported so
# app.core.config.get_settings() picks them up on first call.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("UPLOAD_DIR", "/tmp/pytest_ats_uploads")
os.environ.setdefault("APP_DEBUG", "false")

from app.db.database import Base, get_db  # noqa: E402
from app.models import models  # noqa: E402,F401  (registers tables on Base.metadata)
from app.models.token_blacklist import TokenBlacklist  # noqa: E402,F401
from app.middlewares.rate_limit import limiter  # noqa: E402


@pytest.fixture()
def db_engine():
    """
    Fresh in-memory SQLite engine per test.

    poolclass=StaticPool is required here, not optional: FastAPI's
    TestClient runs request handling in a separate thread (via anyio),
    and SQLAlchemy's default pooling for ':memory:' (SingletonThreadPool)
    hands each thread its own separate connection — which means its own
    separate, empty in-memory database. StaticPool forces every thread to
    share the one connection that actually has tables on it.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()



@pytest.fixture()
def db_session(db_engine) -> Session:
    """One Session per test, reused across every request the test makes."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient wired to the per-test in-memory database."""
    from app.main import app

    limiter.reset()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()



@pytest.fixture()
def auth_headers(client):
    """Registers and logs in a recruiter; returns ready-to-use Authorization headers."""
    client.post("/api/v1/auth/register", json={
        "name": "Jane Doe", "email": "jane@company.com", "password": "SecurePass123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "jane@company.com", "password": "SecurePass123"})
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
