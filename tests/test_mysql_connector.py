"""
tests/test_mysql_connector.py

Mirrors the 5-test structure defined for the PostgreSQL connector (M2W5T9),
run against the MySQL connector (M2W6, rewritten on PyMySQL).

Requires a running MySQL container (see docker-compose.yml -> mysql service).
Connection details are read from environment variables so the same test
file works whether pytest runs on the host machine or inside a container
on the subop-network:

    MYSQL_HOST      default: localhost   (use "mysql" from inside the network)
    MYSQL_PORT      default: 3306
    MYSQL_DATABASE  default: subop
    MYSQL_USER      default: subop_app
    MYSQL_PASSWORD  default: mysql_dev

These defaults match .env.example. Override them in your shell or a
pytest.ini / .env-loading conftest if your local values differ.
"""

import os

import pytest

from services.connectors.errors import ConnectorError
from services.connectors.mysql_connector import (
    MySQLConnector,
    ConnectionConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mysql_config():
    """Valid connection config, read from environment with .env.example defaults."""
    return ConnectionConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database=os.getenv("MYSQL_DATABASE", "subop"),
        username=os.getenv("MYSQL_USER", "subop_app"),
        password=os.getenv("MYSQL_PASSWORD", "mysql_dev"),
    )


@pytest.fixture
def mysql_connection(mysql_config):
    """
    Connects, ensures a clean test_connection table exists (same shape as
    the M1W2T19 PostgreSQL proof: id, name, created_at), and disconnects
    after the test regardless of pass/fail.
    """
    connector = MySQLConnector(mysql_config)
    connector.connect()

    connector.execute_write("""
        CREATE TABLE IF NOT EXISTS test_connection (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    connector.execute_write("TRUNCATE TABLE test_connection")

    yield connector

    connector.disconnect()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_connect_success(mysql_config):
    """A valid config should connect without raising, and hold an open connection."""
    connector = MySQLConnector(mysql_config)
    connector.connect()
    try:
        assert connector.connection is not None
    finally:
        connector.disconnect()


def test_connect_failure(mysql_config):
    """A wrong password should raise ConnectorError, not leak a raw driver exception."""
    bad_config = ConnectionConfig(
        host=mysql_config.host,
        port=mysql_config.port,
        database=mysql_config.database,
        username=mysql_config.username,
        password="definitely_wrong_password",
    )
    connector = MySQLConnector(bad_config)
    with pytest.raises(ConnectorError):
        connector.connect()


def test_execute_query_returns_list(mysql_connection):
    """SELECT should return a list of dict-like rows."""
    mysql_connection.execute_write(
        "INSERT INTO test_connection (name) VALUES (%s)", ("row_a",)
    )
    result = mysql_connection.execute_query(
        "SELECT id, name FROM test_connection WHERE name = %s", ("row_a",)
    )
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "row_a"


def test_execute_write_insert(mysql_connection):
    """INSERT should increase the row count by exactly 1."""
    before = mysql_connection.execute_query(
        "SELECT COUNT(*) AS total FROM test_connection"
    )
    before_count = before[0]["total"]

    affected = mysql_connection.execute_write(
        "INSERT INTO test_connection (name) VALUES (%s)", ("row_b",)
    )
    assert affected == 1

    after = mysql_connection.execute_query(
        "SELECT COUNT(*) AS total FROM test_connection"
    )
    after_count = after[0]["total"]

    assert after_count == before_count + 1


def test_health_check_returns_true(mysql_connection):
    """A healthy, connected database should report True."""
    assert mysql_connection.health_check() is True
