import pytest

from codegar.parser.json import parse_architecture
from codegar.validator.validate import ValidationError, validate_application


def valid_application():
    return parse_architecture(
        {
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
                        "frequency": {
                            "type": "enum",
                            "values": ["daily", "weekly"],
                        },
                    }
                },
                "Completion": {
                    "fields": {
                        "habit": {
                            "type": "reference",
                            "entity": "Habit",
                        }
                    }
                },
            },
            "pages": [
                {
                    "name": "Habits",
                    "route": "/habits",
                    "type": "list",
                    "entity": "Habit",
                }
            ],
        }
    )


def test_valid_application_passes():
    validate_application(valid_application())


def test_invalid_app_name():
    application = valid_application()
    application.name = "habit-tracker"

    with pytest.raises(ValidationError, match="invalid identifier"):
        validate_application(application)


def test_duplicate_entity_names():
    application = valid_application()

    application.entities.append(application.entities[0])

    with pytest.raises(ValidationError, match="duplicate entity name"):
        validate_application(application)


def test_duplicate_field_names():
    application = valid_application()

    entity = application.entities[0]
    entity.fields.append(entity.fields[0])

    with pytest.raises(ValidationError, match="duplicate field name"):
        validate_application(application)


def test_unknown_reference():
    application = valid_application()

    completion = application.entities[1]
    completion.fields[0].entity = "DoesNotExist"

    with pytest.raises(ValidationError, match="unknown entity"):
        validate_application(application)


def test_reference_without_entity():
    application = valid_application()

    completion = application.entities[1]
    completion.fields[0].entity = None

    with pytest.raises(
        ValidationError,
        match="reference field must specify 'entity'",
    ):
        validate_application(application)


def test_duplicate_page_names():
    application = valid_application()

    application.pages.append(
        application.pages[0]
    )

    with pytest.raises(ValidationError, match="duplicate page name"):
        validate_application(application)


def test_duplicate_routes():
    application = valid_application()

    application.pages.append(
        type(application.pages[0])(
            name="OtherPage",
            route="/habits",
            type=application.pages[0].type,
            entity="Habit",
        )
    )

    with pytest.raises(ValidationError, match="duplicate route"):
        validate_application(application)


def test_page_referencing_unknown_entity():
    application = valid_application()

    application.pages[0].entity = "DoesNotExist"

    with pytest.raises(ValidationError, match="unknown entity"):
        validate_application(application)


@pytest.mark.parametrize(
    "route",
    [
        "habits",
        "/habits/",
        "/habits//new",
        "/habits?active=true",
        "/habits/:",
        "/habits/hello world",
    ],
)
def test_invalid_routes(route):
    application = valid_application()
    application.pages[0].route = route

    with pytest.raises(ValidationError):
        validate_application(application)


@pytest.mark.parametrize(
    "route",
    [
        "/",
        "/habits",
        "/habits/new",
        "/habits/:id",
        "/habits/:id/edit",
    ],
)
def test_valid_routes(route):
    application = valid_application()
    application.pages[0].route = route

    validate_application(application)


def test_multiple_validation_errors_are_reported():
    application = valid_application()

    application.name = "invalid-name"
    application.entities[1].fields[0].entity = "Missing"
    application.pages[0].route = "habits"

    with pytest.raises(ValidationError) as exc_info:
        validate_application(application)

    message = str(exc_info.value)

    assert "invalid identifier" in message
    assert "unknown entity" in message
    assert "route must start with '/'" in message
