from decimal import Decimal

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer


class FakeConnector:
    """
    Minimal ConnectorBase-compatible fake used to test
    abstraction-layer delegation without a real database.
    """

    def __init__(self):
        self.query_calls = []
        self.write_calls = []
        self.health_result = True
        self.rows = []

    def execute_query(self, sql, params=None):
        self.query_calls.append((sql, params))
        return self.rows

    def execute_write(self, sql, params=None):
        self.write_calls.append((sql, params))
        return 3

    def health_check(self):
        return self.health_result


def test_execute_query_delegates_to_connector():
    connector = FakeConnector()
    connector.rows = [
        {"id": 1, "name": "Alice"},
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query(
        "SELECT * FROM users",
        {"active": True},
    )

    assert result == [{"id": 1, "name": "Alice"}]
    assert connector.query_calls == [("SELECT * FROM users", {"active": True})]


def test_execute_query_preserves_rows_without_column_metadata():
    connector = FakeConnector()
    connector.rows = [
        {
            "id": 1,
            "name": "Alice",
            "value": None,
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query("SELECT * FROM example")

    assert result == connector.rows


def test_postgresql_query_values_are_normalized():
    connector = FakeConnector()
    connector.rows = [
        {
            "id": 123,
            "amount": Decimal("10.50"),
            "description": "hello",
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query(
        "SELECT id, amount, description FROM example",
        column_types={
            "id": "BIGINT",
            "amount": "NUMERIC(10, 2)",
            "description": "TEXT",
        },
    )

    assert result == [
        {
            "id": 123,
            "amount": Decimal("10.50"),
            "description": "hello",
        }
    ]

    assert isinstance(result[0]["amount"], Decimal)


def test_mysql_json_is_normalized():
    connector = FakeConnector()

    connector.rows = [
        {
            "payload": '{"name": "Alice", "active": true}',
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="mysql",
    )

    result = layer.execute_query(
        "SELECT payload FROM example",
        column_types={
            "payload": "JSON",
        },
    )

    assert result == [
        {
            "payload": {
                "name": "Alice",
                "active": True,
            }
        }
    ]


def test_mysql_tinyint_one_can_use_boolean_schema_intent():
    connector = FakeConnector()

    connector.rows = [
        {
            "enabled": True,
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="mysql",
    )

    result = layer.execute_query(
        "SELECT enabled FROM example",
        column_types={
            "enabled": "TINYINT(1)",
        },
        schema_intents={
            "enabled": "boolean",
        },
    )

    assert result == [
        {
            "enabled": True,
        }
    ]


def test_mssql_binary_value_is_normalized_to_bytes():
    connector = FakeConnector()

    connector.rows = [
        {
            "version": memoryview(b"\x01\x02\x03"),
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="mssql",
    )

    result = layer.execute_query(
        "SELECT version FROM example",
        column_types={
            "version": "ROWVERSION",
        },
    )

    assert result == [
        {
            "version": b"\x01\x02\x03",
        }
    ]

    assert isinstance(result[0]["version"], bytes)


def test_null_remains_none_during_normalization():
    connector = FakeConnector()

    connector.rows = [
        {
            "description": None,
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query(
        "SELECT description FROM example",
        column_types={
            "description": "TEXT",
        },
    )

    assert result == [
        {
            "description": None,
        }
    ]


def test_unknown_columns_are_preserved():
    connector = FakeConnector()

    connector.rows = [
        {
            "id": 1,
            "unmapped": "keep-me",
        }
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query(
        "SELECT id, unmapped FROM example",
        column_types={
            "id": "INTEGER",
        },
    )

    assert result == [
        {
            "id": 1,
            "unmapped": "keep-me",
        }
    ]


def test_column_names_and_row_order_are_preserved():
    connector = FakeConnector()

    connector.rows = [
        {"id": 1, "name": "first"},
        {"id": 2, "name": "second"},
    ]

    layer = AbstractionLayer(
        connector=connector,
        database="postgresql",
    )

    result = layer.execute_query(
        "SELECT id, name FROM example",
        column_types={
            "id": "INTEGER",
            "name": "VARCHAR(100)",
        },
    )

    assert result == [
        {"id": 1, "name": "first"},
        {"id": 2, "name": "second"},
    ]


def test_execute_write_delegates_to_connector():
    connector = FakeConnector()

    layer = AbstractionLayer(
        connector=connector,
        database="mysql",
    )

    result = layer.execute_write(
        "UPDATE users SET active = %s",
        (True,),
    )

    assert result == 3
    assert connector.write_calls == [
        (
            "UPDATE users SET active = %s",
            (True,),
        )
    ]


def test_health_check_delegates_to_connector():
    connector = FakeConnector()
    connector.health_result = True

    layer = AbstractionLayer(
        connector=connector,
        database="mssql",
    )

    assert layer.health_check() is True


def test_health_check_false_is_preserved():
    connector = FakeConnector()
    connector.health_result = False

    layer = AbstractionLayer(
        connector=connector,
        database="mssql",
    )

    assert layer.health_check() is False


def test_connector_exception_is_not_wrapped():
    class FailingConnector:
        def execute_query(self, sql, params=None):
            raise RuntimeError("connector failure")

    layer = AbstractionLayer(
        connector=FailingConnector(),
        database="postgresql",
    )

    with pytest.raises(RuntimeError, match="connector failure"):
        layer.execute_query("SELECT 1")
