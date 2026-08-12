import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from services.connectors.postgres_connector import (  # noqa: E402
    ConnectionConfig,
    PostgresConnector,
)


@pytest.fixture
def test_db_connection():
    config = ConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        database=os.getenv("POSTGRES_DB", "subop"),
        username=os.getenv("POSTGRES_USER", "subop"),
        password=os.getenv("POSTGRES_PASSWORD", "subop_dev"),
    )

    connector = PostgresConnector(config)
    connector.connect()
    yield connector
    connector.disconnect()