import json
from pathlib import Path
from typing import Any

from codegar.ir.model import (
    Application,
    Entity,
    Field,
    FieldType,
    Page,
    PageType,
)


class ArchitectureParseError(ValueError):
    """Raised when architecture.json cannot be converted into the IR."""


def _error(path: str, message: str) -> ArchitectureParseError:
    return ArchitectureParseError(f"{path}: {message}")


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "expected an object")

    return value


def _require_string(
    obj: dict[str, Any],
    key: str,
    path: str,
) -> str:
    if key not in obj:
        raise _error(f"{path}.{key}", "required")

    value = obj[key]

    if not isinstance(value, str):
        raise _error(f"{path}.{key}", "expected a string")

    if not value:
        raise _error(f"{path}.{key}", "must not be empty")

    return value


def _optional_string(
    obj: dict[str, Any],
    key: str,
    path: str,
) -> str | None:
    if key not in obj:
        return None

    value = obj[key]

    if not isinstance(value, str):
        raise _error(f"{path}.{key}", "expected a string")

    return value


def _optional_bool(
    obj: dict[str, Any],
    key: str,
    path: str,
    default: bool = False,
) -> bool:
    if key not in obj:
        return default

    value = obj[key]

    if not isinstance(value, bool):
        raise _error(f"{path}.{key}", "expected a boolean")

    return value


def _parse_field(
    name: str,
    raw: Any,
    path: str,
) -> Field:
    obj = _require_object(raw, path)

    type_name = _require_string(obj, "type", path)

    try:
        field_type = FieldType(type_name)
    except ValueError:
        valid = ", ".join(t.value for t in FieldType)
        raise _error(
            f"{path}.type",
            f"unknown field type '{type_name}'; "
            f"expected one of: {valid}",
        )

    required = _optional_bool(obj, "required", path)

    default = obj.get("default")

    values: list[str] = []
    entity: str | None = None

    if field_type == FieldType.ENUM:
        if "values" not in obj:
            raise _error(
                f"{path}.values",
                "required for enum fields",
            )

        raw_values = obj["values"]

        if not isinstance(raw_values, list):
            raise _error(
                f"{path}.values",
                "expected an array",
            )

        for index, value in enumerate(raw_values):
            if not isinstance(value, str):
                raise _error(
                    f"{path}.values[{index}]",
                    "expected a string",
                )

            if not value:
                raise _error(
                    f"{path}.values[{index}]",
                    "must not be empty",
                )

            values.append(value)

    elif field_type == FieldType.REFERENCE:
        entity = _require_string(obj, "entity", path)

    return Field(
        name=name,
        type=field_type,
        required=required,
        default=default,
        values=values,
        entity=entity,
    )


def _parse_entity(
    name: str,
    raw: Any,
    path: str,
) -> Entity:
    obj = _require_object(raw, path)

    raw_fields = obj.get("fields", {})

    if not isinstance(raw_fields, dict):
        raise _error(
            f"{path}.fields",
            "expected an object",
        )

    fields = [
        _parse_field(
            name=field_name,
            raw=field_value,
            path=f"{path}.fields.{field_name}",
        )
        for field_name, field_value in raw_fields.items()
    ]

    return Entity(
        name=name,
        fields=fields,
    )


def _parse_page(
    raw: Any,
    index: int,
) -> Page:
    path = f"pages[{index}]"
    obj = _require_object(raw, path)

    name = _require_string(obj, "name", path)
    route = _require_string(obj, "route", path)
    type_name = _require_string(obj, "type", path)
    entity = _require_string(obj, "entity", path)

    try:
        page_type = PageType(type_name)
    except ValueError:
        valid = ", ".join(t.value for t in PageType)
        raise _error(
            f"{path}.type",
            f"unknown page type '{type_name}'; "
            f"expected one of: {valid}",
        )

    return Page(
        name=name,
        route=route,
        type=page_type,
        entity=entity,
    )


def parse_architecture(data: dict[str, Any]) -> Application:
    """
    Parse a decoded architecture.json object into the normalized IR.

    This function performs structural validation only.
    Semantic validation is performed by validate_application().
    """

    root = _require_object(data, "$")

    version = _require_string(root, "version", "$")

    raw_app = root.get("app")
    if raw_app is None:
        raise _error("$.app", "required")

    app = _require_object(raw_app, "$.app")

    name = _require_string(app, "name", "$.app")
    title = _require_string(app, "title", "$.app")

    raw_entities = root.get("entities", {})

    if not isinstance(raw_entities, dict):
        raise _error(
            "$.entities",
            "expected an object",
        )

    entities = [
        _parse_entity(
            name=entity_name,
            raw=entity_value,
            path=f"entities.{entity_name}",
        )
        for entity_name, entity_value in raw_entities.items()
    ]

    raw_pages = root.get("pages", [])

    if not isinstance(raw_pages, list):
        raise _error(
            "$.pages",
            "expected an array",
        )

    pages = [
        _parse_page(page, index)
        for index, page in enumerate(raw_pages)
    ]

    return Application(
        version=version,
        name=name,
        title=title,
        entities=entities,
        pages=pages,
    )


def parse_architecture_file(path: str | Path) -> Application:
    """Load and parse an architecture.json file."""

    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise ArchitectureParseError(
            f"{path}: file not found"
        )
    except json.JSONDecodeError as exc:
        raise ArchitectureParseError(
            f"{path}: invalid JSON at line "
            f"{exc.lineno}, column {exc.colno}: {exc.msg}"
        )

    return parse_architecture(data)
