from pathlib import Path

import pytest

from codegar.generators.django import generate_django
from codegar.parser.json import parse_architecture
from codegar.validator.validate import ValidationError, validate_application


def make_application():
    return parse_architecture(
        {
            "version": "0.1",
            "app": {
                "name": "inventory",
                "title": "Inventory",
            },
            "entities": {
                "Product": {
                    "fields": {
                        "name": {
                            "type": "string",
                            "required": True,
                        },
                        "quantity": {
                            "type": "integer",
                            "required": True,
                            "default": 0,
                        },
                        "price": {
                            "type": "number",
                        },
                        "active": {
                            "type": "boolean",
                            "required": True,
                            "default": True,
                        },
                        "released": {
                            "type": "date",
                        },
                        "created_at": {
                            "type": "datetime",
                        },
                        "category": {
                            "type": "enum",
                            "values": ["hardware", "software"],
                            "default": "hardware",
                        },
                    }
                },
                "StockEntry": {
                    "fields": {
                        "product": {
                            "type": "reference",
                            "entity": "Product",
                            "required": True,
                        }
                    }
                },
            },
            "pages": [
                {
                    "name": "Products",
                    "route": "/products",
                    "type": "list",
                    "entity": "Product",
                }
            ],
        }
    )


def generate(tmp_path: Path):
    application = make_application()
    generate_django(application, tmp_path)
    return tmp_path


def test_generates_expected_project_structure(tmp_path):
    output = generate(tmp_path)

    expected_files = [
        "requirements.txt",
        "backend/manage.py",
        "backend/config/__init__.py",
        "backend/config/settings.py",
        "backend/config/urls.py",
        "backend/config/wsgi.py",
        "backend/config/asgi.py",
        "backend/inventory/__init__.py",
        "backend/inventory/apps.py",
        "backend/inventory/models.py",
        "backend/inventory/admin.py",
        "backend/inventory/views.py",
        "backend/inventory/tests.py",
    ]

    for relative_path in expected_files:
        assert (output / relative_path).is_file(), relative_path


def test_generates_requirements(tmp_path):
    output = generate(tmp_path)

    requirements = (output / "requirements.txt").read_text()

    assert "Django>=5.0,<6.0" in requirements


def test_generates_models(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert "class Product(models.Model):" in models
    assert "class StockEntry(models.Model):" in models


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("name", "models.CharField(max_length=255"),
        ("quantity", "models.IntegerField("),
        ("price", "models.FloatField("),
        ("active", "models.BooleanField("),
        ("released", "models.DateField("),
        ("created_at", "models.DateTimeField("),
    ],
)
def test_field_type_mappings(tmp_path, field, expected):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    line = next(
        line for line in models.splitlines()
        if line.strip().startswith(f"{field} =")
    )

    assert expected in line


def test_enum_generates_choices(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert (
        "choices=[('hardware', 'hardware'), "
        "('software', 'software')]"
    ) in models


def test_default_values_are_generated(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert "quantity = models.IntegerField(default=0)" in models
    assert "active = models.BooleanField(default=True)" in models
    assert "default='hardware'" in models


def test_optional_fields_are_nullable(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert (
        "name = models.CharField(max_length=255)"
        in models
    )

    assert (
        "price = models.FloatField(null=True, blank=True)"
        in models
    )

    assert (
        "released = models.DateField(null=True, blank=True)"
        in models
    )


def test_reference_generates_foreign_key(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert (
        'product = models.ForeignKey("Product", '
        "on_delete=models.CASCADE)"
    ) in models


def test_reference_respects_optional_field(tmp_path):
    application = make_application()

    product = application.entities[1]
    product.fields[0].required = False

    output = tmp_path
    generate_django(application, output)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert (
        'product = models.ForeignKey("Product", '
        "on_delete=models.CASCADE, null=True, blank=True)"
    ) in models


def test_model_has_string_representation(tmp_path):
    output = generate(tmp_path)

    models = (
        output / "backend/inventory/models.py"
    ).read_text()

    assert "def __str__(self):" in models
    assert "return str(self.name)" in models


def test_app_config_uses_application_name(tmp_path):
    output = generate(tmp_path)

    apps = (
        output / "backend/inventory/apps.py"
    ).read_text()

    assert "class InventoryConfig(AppConfig):" in apps
    assert 'name = "inventory"' in apps


def test_settings_register_generated_app(tmp_path):
    output = generate(tmp_path)

    settings = (
        output / "backend/config/settings.py"
    ).read_text()

    assert '"inventory",' in settings


def test_invalid_architecture_is_rejected_before_generation(tmp_path):
    application = make_application()
    application.entities[1].fields[0].entity = "DoesNotExist"

    with pytest.raises(ValidationError, match="unknown entity"):
        validate_application(application)

    # The generator itself intentionally assumes validated IR.
    # The compiler/CLI is responsible for validation before generation.
    assert not (tmp_path / "backend").exists()


def test_unsupported_field_type_fails_generation(tmp_path):
    application = make_application()

    application.entities[0].fields[0].type = object()

    with pytest.raises(ValueError, match="Unsupported field type"):
        generate_django(application, tmp_path)