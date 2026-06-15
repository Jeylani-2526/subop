import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from services.connectors.postgres_connector import (
    ConnectionConfig,
    PostgresConnector
)


@pytest.fixture
def test_db_connection():
    config = ConnectionConfig(
        host="127.0.0.1",
        port=5432,
        database="subop",
        username="subop",
        password="subop_dev"
    )

    connector = PostgresConnector(config)

    connector.connect()

    yield connector

    connector.disconnect()