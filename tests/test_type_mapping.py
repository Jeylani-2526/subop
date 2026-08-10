import pytest
from decimal import Decimal

from services.abstraction.type_mapping import (
    UniversalTypeMapper,
    UnsupportedTypeError,
    normalize_value,
)


def test_postgresql_text_maps_to_text():
    result = UniversalTypeMapper.map_type(
        "postgresql",
        "TEXT",
    )

    assert result.canonical_type == "TEXT"
    assert result.condition == "direct"
    assert result.metadata["postgresql_text"] is True


def test_postgresql_bigint_maps_to_bigint():
    result = UniversalTypeMapper.map_type(
        "postgresql",
        "BIGINT",
    )

    assert result.canonical_type == "BIGINT"
    assert result.condition == "direct"


def test_postgresql_double_precision_is_inexact_decimal():
    result = UniversalTypeMapper.map_type(
        "postgresql",
        "DOUBLE PRECISION",
    )

    assert result.canonical_type == "DECIMAL"
    assert result.condition == "inexact"
    assert result.metadata["inexact"] is True


def test_mysql_varchar_maps_to_varchar():
    result = UniversalTypeMapper.map_type(
        "mysql",
        "VARCHAR(255)",
    )

    assert result.canonical_type == "VARCHAR"
    assert result.condition == "direct"


def test_mysql_int_unsigned_maps_to_bigint():
    result = UniversalTypeMapper.map_type(
        "mysql",
        "INT UNSIGNED",
    )

    assert result.canonical_type == "BIGINT"
    assert result.metadata["unsigned"] is True


def test_mysql_tinyint_one_is_ambiguous_integer_by_default():
    result = UniversalTypeMapper.map_type(
        "mysql",
        "TINYINT(1)",
    )

    assert result.canonical_type == "INTEGER"
    assert result.condition == "ambiguous"
    assert result.metadata["ambiguous_boolean"] is True


def test_mysql_tinyint_one_can_be_boolean_with_schema_intent():
    result = UniversalTypeMapper.map_type(
        "mysql",
        "TINYINT(1)",
        schema_intent="boolean",
    )

    assert result.canonical_type == "BOOLEAN"
    assert result.condition == "ambiguous"


def test_mssql_nvarchar_max_maps_to_text():
    result = UniversalTypeMapper.map_type(
        "mssql",
        "NVARCHAR(MAX)",
    )

    assert result.canonical_type == "TEXT"
    assert result.metadata["unicode"] is True
    assert result.metadata["max_length"] is True


def test_mssql_timestamp_maps_to_binary():
    result = UniversalTypeMapper.map_type(
        "mssql",
        "TIMESTAMP",
    )

    assert result.canonical_type == "BINARY"
    assert result.metadata["rowversion_semantics"] is True


def test_mssql_uniqueidentifier_falls_back_to_varchar():
    result = UniversalTypeMapper.map_type(
        "mssql",
        "UNIQUEIDENTIFIER",
    )

    assert result.canonical_type == "VARCHAR"
    assert result.condition == "fallback"
    assert result.metadata["uuid_semantics"] is True


def test_sql_null_remains_none():
    assert normalize_value(None) is None


def test_memoryview_becomes_bytes():
    value = memoryview(b"hello")

    result = normalize_value(
        value,
        canonical_type="BINARY",
    )

    assert result == b"hello"
    assert isinstance(result, bytes)


def test_decimal_is_preserved():
    value = Decimal("123.45")

    result = normalize_value(
        value,
        canonical_type="DECIMAL",
    )

    assert result == Decimal("123.45")
    assert isinstance(result, Decimal)


def test_json_text_is_parsed_only_with_json_canonical_type():
    result = normalize_value(
        '{"name": "omer"}',
        canonical_type="JSON",
    )

    assert result == {"name": "omer"}


def test_unknown_type_raises_error():
    with pytest.raises(UnsupportedTypeError):
        UniversalTypeMapper.map_type(
            "postgresql",
            "SOME_UNKNOWN_TYPE",
        )