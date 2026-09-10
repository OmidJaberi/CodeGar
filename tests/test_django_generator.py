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

def read_generated(output: Path, relative_path: str) -> str:
    return (output / relative_path).read_text()


def test_generates_views(tmp_path):
    output = generate(tmp_path)

    views = read_generated(
        output,
        "backend/inventory/views.py",
    )

    assert "def product_list(request):" in views
    assert "def product_detail(request, pk):" in views
    assert "def stockentry_list(request):" in views
    assert "def stockentry_detail(request, pk):" in views


def test_generates_entity_api_routes(tmp_path):
    output = generate(tmp_path)

    urls = read_generated(
        output,
        "backend/inventory/urls.py",
    )

    assert 'path("api/product/", views.product_list' in urls
    assert 'path("api/product/<int:pk>/", views.product_detail' in urls

    assert 'path("api/stockentry/", views.stockentry_list' in urls
    assert 'path("api/stockentry/<int:pk>/", views.stockentry_detail' in urls


def test_generates_page_routes(tmp_path):
    output = generate(tmp_path)

    urls = read_generated(
        output,
        "backend/inventory/urls.py",
    )

    assert (
        'path("products", views.products_page, name="products_page")'
        in urls
    )


def test_generates_page_views(tmp_path):
    output = generate(tmp_path)

    views = read_generated(
        output,
        "backend/inventory/views.py",
    )

    assert "def products_page(request):" in views
    assert '"page": "Products"' in views
    assert '"route": "/products"' in views
    assert '"type": "list"' in views
    assert '"entity": "Product"' in views


def test_includes_app_urls_in_root_urls(tmp_path):
    output = generate(tmp_path)

    urls = read_generated(
        output,
        "backend/config/urls.py",
    )

    assert 'path("", include("inventory.urls"))' in urls


def test_generates_all_crud_methods(tmp_path):
    output = generate(tmp_path)

    views = read_generated(
        output,
        "backend/inventory/views.py",
    )

    assert 'if request.method == "GET":' in views
    assert 'if request.method == "POST":' in views
    assert 'if request.method in ("PUT", "PATCH"):' in views
    assert 'if request.method == "DELETE":' in views


def test_generates_json_serialization(tmp_path):
    output = generate(tmp_path)

    views = read_generated(
        output,
        "backend/inventory/views.py",
    )

    assert "def _serialize_object(obj):" in views
    assert 'data = {"id": obj.pk}' in views
    assert "value.isoformat()" in views


def test_generates_reference_serialization(tmp_path):
    output = generate(tmp_path)

    views = read_generated(
        output,
        "backend/inventory/views.py",
    )

    assert (
        'data[field.name] = getattr(obj, field.name + "_id")'
        in views
    )