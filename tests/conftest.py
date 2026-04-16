"""Pytest fixtures and environment defaults for isolated integration tests."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("MCP_API_KEY", "test-api-key")
os.environ.setdefault("REQUIRE_TENANT_HEADER", "false")
os.environ.setdefault("DEFAULT_TENANT_ID", "tenant-a")

import pytest

from enterprise_mcp.data.db import Base, engine, init_database


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Reset database schema and seed defaults before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_database()
