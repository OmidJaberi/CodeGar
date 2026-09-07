import re

from codegar.ir.model import Application, Entity, FieldType


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ROUTE_RE = re.compile(r"^/(?:[^/]*/)*[^/]*$")


class ValidationError(ValueError):
    """A single architecture validation error."""


def _validate_identifier(
    value: str,
    path: str,
    errors: list[str],
) -> None:
    if not _IDENTIFIER_RE.fullmatch(value):
        errors.append(
            f"{path}: invalid identifier '{value}'"
        )


def _validate_route(
    route: str,
    path: str,
    errors: list[str],
) -> None:
    if not route.startswith("/"):
        errors.append(
            f"{path}: route must start with '/'"
        )
        return

    if "?" in route:
        errors.append(
            f"{path}: query parameters are not allowed in routes"
        )

    if "//" in route:
        errors.append(
            f"{path}: route must not contain '//'"
        )

    if route != "/" and route.endswith("/"):
        errors.append(
            f"{path}: route must not end with '/'"
        )

    for segment in route.split("/")[1:]:
        if not segment:
            continue

        if segment.startswith(":"):
            if len(segment) == 1:
                errors.append(
                    f"{path}: empty route parameter"
                )
        elif not re.fullmatch(
            r"[A-Za-z0-9_.~-]+",
            segment,
        ):
            errors.append(
                f"{path}: invalid route segment '{segment}'"
            )


def validate_application(
    application: Application,
) -> None:
    """
    Validate semantic invariants of an Application IR.

    Raises ValidationError containing all discovered errors.
    """

    errors: list[str] = []

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    _validate_identifier(
        application.name,
        "app.name",
        errors,
    )

    # ---------------------------------------------------------
    # Entities
    # ---------------------------------------------------------

    entity_names: set[str] = set()

    for entity in application.entities:
        path = f"entities.{entity.name}"

        if entity.name in entity_names:
            errors.append(
                f"{path}: duplicate entity name"
            )
            continue

        entity_names.add(entity.name)

        _validate_identifier(
            entity.name,
            f"{path}",
            errors,
        )

        field_names: set[str] = set()

        for field in entity.fields:
            field_path = f"{path}.fields.{field.name}"

            if field.name in field_names:
                errors.append(
                    f"{field_path}: duplicate field name"
                )
                continue

            field_names.add(field.name)

            _validate_identifier(
                field.name,
                field_path,
                errors,
            )

            # Enum invariants
            if field.type == FieldType.ENUM:
                if not field.values:
                    errors.append(
                        f"{field_path}: enum must have at least "
                        f"one value"
                    )

                if len(field.values) != len(set(field.values)):
                    errors.append(
                        f"{field_path}: enum values must be unique"
                    )

                for index, value in enumerate(field.values):
                    if not value:
                        errors.append(
                            f"{field_path}.values[{index}]: "
                            f"must not be empty"
                        )

            elif field.values:
                errors.append(
                    f"{field_path}: 'values' is only valid "
                    f"for enum fields"
                )

            # Reference invariants
            if field.type == FieldType.REFERENCE:
                if not field.entity:
                    errors.append(
                        f"{field_path}: reference field must "
                        f"specify 'entity'"
                    )

            elif field.entity is not None:
                errors.append(
                    f"{field_path}: 'entity' is only valid "
                    f"for reference fields"
                )

    # ---------------------------------------------------------
    # Resolve references
    # ---------------------------------------------------------

    for entity in application.entities:
        for field in entity.fields:
            if (
                field.type == FieldType.REFERENCE
                and field.entity is not None
                and field.entity not in entity_names
            ):
                errors.append(
                    f"entities.{entity.name}.fields.{field.name}.entity: "
                    f"unknown entity '{field.entity}'"
                )

    # ---------------------------------------------------------
    # Pages
    # ---------------------------------------------------------

    page_names: set[str] = set()
    routes: set[str] = set()

    for index, page in enumerate(application.pages):
        path = f"pages[{index}]"

        if page.name in page_names:
            errors.append(
                f"{path}.name: duplicate page name '{page.name}'"
            )

        page_names.add(page.name)

        _validate_identifier(
            page.name,
            f"{path}.name",
            errors,
        )

        if page.route in routes:
            errors.append(
                f"{path}.route: duplicate route '{page.route}'"
            )

        routes.add(page.route)

        _validate_route(
            page.route,
            f"{path}.route",
            errors,
        )

        if page.entity not in entity_names:
            errors.append(
                f"{path}.entity: unknown entity "
                f"'{page.entity}'"
            )

    # ---------------------------------------------------------
    # Fail once, with all errors
    # ---------------------------------------------------------

    if errors:
        raise ValidationError(
            "Architecture validation failed:\n"
            + "\n".join(f"  - {error}" for error in errors)
        )
