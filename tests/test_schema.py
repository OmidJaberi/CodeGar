import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schema" / "architecture.schema.json"


def load_schema():
    with SCHEMA_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def test_schema_is_valid():
    schema = load_schema()
    Draft202012Validator.check_schema(schema)


def test_minimal_architecture_is_valid():
    schema = load_schema()

    architecture = {
        "version": "0.1",
        "app": {
            "name": "todo",
            "title": "Todo",
        },
    }

    errors = list(
        Draft202012Validator(schema).iter_errors(architecture)
    )

    assert errors == []


def test_unknown_field_type_is_rejected():
    schema = load_schema()

    architecture = {
        "version": "0.1",
        "app": {
            "name": "todo",
            "title": "Todo",
        },
        "entities": {
            "Todo": {
                "fields": {
                    "name": {
                        "type": "uuid",
                    }
                }
            }
        },
    }

    errors = list(
        Draft202012Validator(schema).iter_errors(architecture)
    )

    assert errors


def test_unknown_properties_are_rejected():
    schema = load_schema()

    architecture = {
        "version": "0.1",
        "app": {
            "name": "todo",
            "title": "Todo",
            "django_model": "TodoModel",
        },
    }

    errors = list(
        Draft202012Validator(schema).iter_errors(architecture)
    )

    assert errors
