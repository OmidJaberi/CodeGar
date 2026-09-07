import pytest

from codegar.parser.json import (
    ArchitectureParseError,
    parse_architecture,
)
from codegar.ir.model import FieldType, PageType


def valid_architecture():
    return {
        "version": "0.1",
        "app": {
            "name": "habit_tracker",
            "title": "Habit Tracker",
        },
        "entities": {
            "Habit": {
                "fields": {
                    "name": {
                        "type": "string",
                        "required": True,
                    },
                    "active": {
                        "type": "boolean",
                        "required": True,
                        "default": True,
                    },
                    "frequency": {
                        "type": "enum",
                        "values": ["daily", "weekly"],
                        "required": True,
                    },
                }
            },
            "Completion": {
                "fields": {
                    "habit": {
                        "type": "reference",
                        "entity": "Habit",
                        "required": True,
                    },
                    "completed_at": {
                        "type": "datetime",
                        "required": True,
                    },
                }
            },
        },
        "pages": [
            {
                "name": "Habits",
                "route": "/habits",
                "type": "list",
                "entity": "Habit",
            },
            {
                "name": "NewHabit",
                "route": "/habits/new",
                "type": "create",
                "entity": "Habit",
            },
        ],
    }


def test_parse_minimal_application():
    application = parse_architecture(
        {
            "version": "0.1",
            "app": {
                "name": "todo",
                "title": "Todo",
            },
        }
    )

    assert application.version == "0.1"
    assert application.name == "todo"
    assert application.title == "Todo"
    assert application.entities == []
    assert application.pages == []


def test_parse_entities_into_normalized_ir():
    application = parse_architecture(valid_architecture())

    assert [entity.name for entity in application.entities] == [
        "Habit",
        "Completion",
    ]

    habit = application.entities[0]

    assert [field.name for field in habit.fields] == [
        "name",
        "active",
        "frequency",
    ]

    assert habit.fields[0].type == FieldType.STRING
    assert habit.fields[0].required is True

    assert habit.fields[1].type == FieldType.BOOLEAN
    assert habit.fields[1].default is True

    assert habit.fields[2].type == FieldType.ENUM
    assert habit.fields[2].values == ["daily", "weekly"]


def test_parse_reference_field():
    application = parse_architecture(valid_architecture())

    completion = application.entities[1]
    habit_field = completion.fields[0]

    assert habit_field.type == FieldType.REFERENCE
    assert habit_field.entity == "Habit"


def test_parse_pages():
    application = parse_architecture(valid_architecture())

    assert len(application.pages) == 2

    page = application.pages[0]

    assert page.name == "Habits"
    assert page.route == "/habits"
    assert page.type == PageType.LIST
    assert page.entity == "Habit"


def test_unknown_field_type_is_rejected():
    architecture = valid_architecture()
    architecture["entities"]["Habit"]["fields"]["name"]["type"] = "uuid"

    with pytest.raises(ArchitectureParseError, match="unknown field type"):
        parse_architecture(architecture)


def test_unknown_page_type_is_rejected():
    architecture = valid_architecture()
    architecture["pages"][0]["type"] = "dashboard"

    with pytest.raises(ArchitectureParseError, match="unknown page type"):
        parse_architecture(architecture)


def test_missing_required_property_is_rejected():
    architecture = valid_architecture()
    del architecture["app"]["name"]

    with pytest.raises(ArchitectureParseError, match=r"\$\.app\.name: required"):
        parse_architecture(architecture)


def test_enum_requires_values():
    architecture = valid_architecture()
    del architecture["entities"]["Habit"]["fields"]["frequency"]["values"]

    with pytest.raises(
        ArchitectureParseError,
        match=r"values: required for enum fields",
    ):
        parse_architecture(architecture)


def test_reference_requires_entity():
    architecture = valid_architecture()
    del architecture["entities"]["Completion"]["fields"]["habit"]["entity"]

    with pytest.raises(
        ArchitectureParseError,
        match=r"entity: required",
    ):
        parse_architecture(architecture)
