import pytest

from app.services.model.mapper import map_json_schema_to_mysql, validate_json_schema


def test_map_string_to_varchar() -> None:
    result = map_json_schema_to_mysql("string", {"maxLength": 100})
    assert result == "VARCHAR(100)"


def test_map_string_long_to_text() -> None:
    result = map_json_schema_to_mysql("string", {"maxLength": 10000})
    assert result == "TEXT"


def test_map_number_to_decimal() -> None:
    result = map_json_schema_to_mysql("number", {})
    assert result == "DECIMAL(19,4)"


def test_map_integer_to_bigint() -> None:
    result = map_json_schema_to_mysql("integer", {})
    assert result == "BIGINT"


def test_map_boolean_to_tinyint() -> None:
    result = map_json_schema_to_mysql("boolean", {})
    assert result == "TINYINT(1)"


def test_map_date_to_datetime() -> None:
    result = map_json_schema_to_mysql("string", {"format": "date-time"})
    assert result == "DATETIME"


def test_map_json_to_json() -> None:
    result = map_json_schema_to_mysql("object", {})
    assert result == "JSON"


def test_validate_json_schema_valid() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
    }
    assert validate_json_schema(schema) == []


def test_validate_json_schema_missing_type() -> None:
    schema: dict[str, object] = {
        "properties": {
            "name": {"type": "string"},
        },
    }
    errors = validate_json_schema(schema)
    assert errors == ["JSON Schema root must be type 'object'"]


def test_validate_json_schema_no_properties() -> None:
    schema: dict[str, object] = {"type": "object"}
    errors = validate_json_schema(schema)
    assert errors == ["JSON Schema must have at least one property"]


def test_validate_json_schema_property_missing_type() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "name": {},
        },
    }
    errors = validate_json_schema(schema)
    assert "Property 'name' missing 'type'" in errors


def test_validate_json_schema_property_not_object() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "name": "string",
        },
    }
    errors = validate_json_schema(schema)
    assert "Property 'name' must be an object" in errors
