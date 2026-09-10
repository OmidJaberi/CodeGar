from pathlib import Path

from codegar.ir.model import Application, Entity, Field, FieldType


def generate_django(application: Application, output: str | Path) -> None:
    output = Path(output)

    backend = output / "backend"
    config = backend / "config"
    app = backend / application.name

    config.mkdir(parents=True, exist_ok=True)
    app.mkdir(parents=True, exist_ok=True)

    _write(output / "requirements.txt", "Django>=5.0,<6.0\n")
    _write(backend / "manage.py", _manage_py())
    _write(config / "__init__.py", "")
    _write(config / "settings.py", _settings_py(application.name))
    _write(config / "urls.py", _urls_py(application.name))
    _write(config / "wsgi.py", _wsgi_py())
    _write(config / "asgi.py", _asgi_py())

    _write(app / "__init__.py", "")
    _write(app / "apps.py", _apps_py(application.name))
    _write(app / "models.py", _models_py(application))
    _write(app / "admin.py", _admin_py(application))
    _write(app / "views.py", _views_py(application))
    _write(app / "urls.py", _app_urls_py(application))
    _write(app / "tests.py", "")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _manage_py() -> str:
    return '''#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''


def _settings_py(app_name: str) -> str:
    return f'''from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "codegar-development-only"

DEBUG = True

ALLOWED_HOSTS = []


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "{app_name}",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {{
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        }},
    }},
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {{
    "default": {{
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }}
}}


AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'''


def _urls_py(app_name: str) -> str:
    return f'''from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("{app_name}.urls")),
]
'''


def _wsgi_py() -> str:
    return '''import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
'''


def _asgi_py() -> str:
    return '''import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
'''


def _apps_py(app_name: str) -> str:
    class_name = "".join(part.capitalize() for part in app_name.split("_"))

    return f'''from django.apps import AppConfig


class {class_name}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app_name}"
'''


def _models_py(application: Application) -> str:
    lines = [
        "from django.db import models",
        "",
        "",
    ]

    for entity in application.entities:
        lines.extend(_model(entity))
        lines.append("")

    return "\n".join(lines)


def _model(entity: Entity) -> list[str]:
    lines = [
        f"class {entity.name}(models.Model):",
    ]

    if not entity.fields:
        lines.append("    pass")
    else:
        for field in entity.fields:
            lines.append(f"    {field.name} = {_django_field(field)}")

    lines.extend(
        [
            "",
            "    def __str__(self):",
            f"        return str(self.{_display_field(entity)})",
        ]
    )

    return lines


def _display_field(entity: Entity) -> str:
    if entity.fields:
        return entity.fields[0].name

    return "id"


def _django_field(field: Field) -> str:
    options = []

    if not field.required:
        options.append("null=True")
        options.append("blank=True")

    if field.default is not None:
        options.append(f"default={field.default!r}")

    suffix = ", " + ", ".join(options) if options else ""

    if field.type == FieldType.STRING:
        return f"models.CharField(max_length=255{suffix})"

    if field.type == FieldType.INTEGER:
        return f"models.IntegerField({', '.join(options)})" if options else "models.IntegerField()"

    if field.type == FieldType.NUMBER:
        return f"models.FloatField({', '.join(options)})" if options else "models.FloatField()"

    if field.type == FieldType.BOOLEAN:
        return f"models.BooleanField({', '.join(options)})" if options else "models.BooleanField()"

    if field.type == FieldType.DATE:
        return f"models.DateField({', '.join(options)})" if options else "models.DateField()"

    if field.type == FieldType.DATETIME:
        return f"models.DateTimeField({', '.join(options)})" if options else "models.DateTimeField()"

    if field.type == FieldType.ENUM:
        choices = ", ".join(
            f"({value!r}, {value!r})"
            for value in field.values
        )

        if options:
            return (
                f"models.CharField("
                f"max_length=255, "
                f"choices=[{choices}], "
                f"{', '.join(options)}"
                f")"
            )

        return f"models.CharField(max_length=255, choices=[{choices}])"

    if field.type == FieldType.REFERENCE:
        if not field.entity:
            raise ValueError(
                f"Reference field '{field.name}' has no target entity"
            )

        reference_options = ["on_delete=models.CASCADE"]

        if not field.required:
            reference_options.extend(["null=True", "blank=True"])

        if field.default is not None:
            reference_options.append(f"default={field.default!r}")

        return (
            f'models.ForeignKey("{field.entity}", '
            f"{', '.join(reference_options)})"
        )

    raise ValueError(f"Unsupported field type: {field.type}")


def _views_py(application: Application) -> str:
    lines = [
        "import json",
        "",
        "from django.http import JsonResponse",
        "from django.views.decorators.csrf import csrf_exempt",
        "",
        f"from .models import {', '.join(entity.name for entity in application.entities)}",
        "",
        "",
    ]

    for entity in application.entities:
        lines.extend(_entity_views(entity))
        lines.append("")

    for page in application.pages:
        lines.extend(_page_view(page))
        lines.append("")

    return "\n".join(lines)


def _entity_views(entity: Entity) -> list[str]:
    name = entity.name

    return [
        "@csrf_exempt",
        f"def {name.lower()}_list(request):",
        "    if request.method == \"GET\":",
        f"        objects = {name}.objects.all()",
        "        return JsonResponse(",
        "            {\"data\": [_serialize_object(obj) for obj in objects]}"
        "        )",
        "",
        "    if request.method == \"POST\":",
        "        try:",
        "            data = json.loads(request.body or \"{}\")",
        "        except json.JSONDecodeError:",
        "            return JsonResponse({\"error\": \"Invalid JSON\"}, status=400)",
        "",
        f"        obj = {name}()",
        "        _update_object(obj, data)",
        "        obj.save()",
        "        return JsonResponse(",
        "            {\"data\": _serialize_object(obj)},",
        "            status=201,",
        "        )",
        "",
        "    return JsonResponse(",
        "        {\"error\": \"Method not allowed\"},",
        "        status=405,",
        "    )",
        "",
        "",
        "@csrf_exempt",
        f"def {name.lower()}_detail(request, pk):",
        f"    try:",
        f"        obj = {name}.objects.get(pk=pk)",
        "    except " + name + ".DoesNotExist:",
        "        return JsonResponse({\"error\": \"Not found\"}, status=404)",
        "",
        "    if request.method == \"GET\":",
        "        return JsonResponse({\"data\": _serialize_object(obj)})",
        "",
        "    if request.method in (\"PUT\", \"PATCH\"):",
        "        try:",
        "            data = json.loads(request.body or \"{}\")",
        "        except json.JSONDecodeError:",
        "            return JsonResponse({\"error\": \"Invalid JSON\"}, status=400)",
        "",
        "        _update_object(obj, data)",
        "        obj.save()",
        "        return JsonResponse({\"data\": _serialize_object(obj)})",
        "",
        "    if request.method == \"DELETE\":",
        "        obj.delete()",
        "        return JsonResponse({\"data\": None})",
        "",
        "    return JsonResponse(",
        "        {\"error\": \"Method not allowed\"},",
        "        status=405,",
        "    )",
        "",
        "",
        "def _serialize_object(obj):",
        "    data = {\"id\": obj.pk}",
        "    for field in obj._meta.fields:",
        "        if field.name == \"id\":",
        "            continue",
        "        value = getattr(obj, field.name)",
        "",
        "        if hasattr(value, \"isoformat\"):",
        "            value = value.isoformat()",
        "",
        "        if field.is_relation:",
        "            data[field.name] = getattr(obj, field.name + \"_id\")",
        "        else:",
        "            data[field.name] = value",
        "",
        "    return data",
        "",
        "",
        "def _update_object(obj, data):",
        "    for field in obj._meta.fields:",
        "        if field.name == \"id\" or field.name not in data:",
        "            continue",
        "",
        "        if field.is_relation:",
        "            setattr(obj, field.name + \"_id\", data[field.name])",
        "        else:",
        "            setattr(obj, field.name, data[field.name])",
    ]


def _page_view(page) -> list[str]:
    function_name = _page_function_name(page.name)

    return [
        f"def {function_name}(request):",
        "    return JsonResponse(",
        "        {",
        f'            "page": "{page.name}",',
        f'            "route": "{page.route}",',
        f'            "type": "{page.type.value}",',
        f'            "entity": "{page.entity}",',
        "        }",
        "    )",
    ]


def _page_function_name(name: str) -> str:
    return (
        name.lower()
        .replace("-", "_")
        .replace(" ", "_")
    ) + "_page"


def _app_urls_py(application: Application) -> str:
    lines = [
        "from django.urls import path",
        "",
        "from . import views",
        "",
        "",
        "urlpatterns = [",
    ]

    for entity in application.entities:
        name = entity.name.lower()

        lines.extend(
            [
                f'    path("api/{name}/", views.{name}_list, name="{name}-list"),',
                f'    path("api/{name}/<int:pk>/", views.{name}_detail, name="{name}-detail"),',
            ]
        )

    for page in application.pages:
        function_name = _page_function_name(page.name)

        route = page.route.lstrip("/")

        lines.append(
            f'    path("{route}", views.{function_name}, name="{function_name}"),'
        )

    lines.append("]")

    return "\n".join(lines) + "\n"


def _admin_py(application: Application) -> str:
    lines = [
        "from django.contrib import admin",
        "",
    ]

    for entity in application.entities:
        lines.append(f"from .models import {entity.name}")

    lines.append("")

    for entity in application.entities:
        lines.append(f"admin.site.register({entity.name})")

    lines.append("")

    return "\n".join(lines)