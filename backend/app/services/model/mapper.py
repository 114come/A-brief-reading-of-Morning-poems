from typing import Any

# JSON Schema 类型 → MySQL 类型映射
JSON_SCHEMA_TO_MYSQL: dict[str, str] = {
    "string": "VARCHAR",
    "text": "TEXT",
    "number": "DECIMAL",
    "integer": "BIGINT",
    "boolean": "TINYINT(1)",
    "date": "DATE",
    "datetime": "DATETIME",
    "file": "VARCHAR(500)",
    "json": "JSON",
    "object": "JSON",
    "array": "JSON",
}


def map_json_schema_to_mysql(
    field_type: str,
    constraints: dict[str, Any],
) -> str:
    """将 JSON Schema 字段类型映射为 MySQL 列类型"""
    if field_type == "string":
        max_length = constraints.get("maxLength", 255)
        if max_length >= 5000:
            return "TEXT"
        if constraints.get("format") == "date-time":
            return "DATETIME"
        if constraints.get("format") == "date":
            return "DATE"
        return f"VARCHAR({min(max_length, 4000)})"

    if field_type == "number":
        precision = constraints.get("precision", 19)
        scale = constraints.get("scale", 4)
        return f"DECIMAL({precision},{scale})"

    if field_type == "integer":
        return "BIGINT"

    if field_type == "boolean":
        return "TINYINT(1)"

    if field_type in ("object", "array", "json"):
        return "JSON"

    if field_type == "file":
        return "VARCHAR(500)"

    if field_type in ("date", "datetime"):
        return field_type.upper()

    # 默认 fallback
    return "TEXT"


def validate_json_schema(schema: dict[str, Any]) -> list[str]:
    """验证 JSON Schema 是否合法，返回错误列表"""
    errors: list[str] = []
    if schema.get("type") != "object":
        errors.append("JSON Schema root must be type 'object'")
        return errors

    properties = schema.get("properties", {})
    if not properties:
        errors.append("JSON Schema must have at least one property")

    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            errors.append(f"Property '{prop_name}' must be an object")
            continue
        if "type" not in prop_def:
            errors.append(f"Property '{prop_name}' missing 'type'")

    return errors
