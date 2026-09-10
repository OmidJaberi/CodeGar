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
    _write(backend / "manage.py", _manage_py(application.name))
    _write(config / "__init__.py", "")
    _write(config / "settings.py", _settings_py(application.name))
    _write(config / "urls.py", _urls_py(application.name))
    _write(config / "wsgi.py", _wsgi_py(application.name))
    _write(config / "asgi.py", _asgi_py(application.name))

    _write(app / "__init__.py", "")
    _write(app / "apps.py", _apps_py(application.name))
    _write(app / "models.py", _models_py(application))
    _write(app / "admin.py", _admin_py(application.name))
    _write(app / "views.py", "")
    _write(app / "tests.py", "")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _manage_py(app_name: str) -> str:
    return f'''#!/usr/bin/env python
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
    return '''from django.contrib import admin
from django.urls import path


urlpatterns = [
    path("admin/", admin.site.urls),
]
'''


def _wsgi_py(app_name: str) -> str:
    return '''import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
'''


def _asgi_py(app_name: str) -> str:
    return '''import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
'''


def _apps_py(app_name: str) -> str:
    return f'''from django.apps import AppConfig


class {app_name.title().replace("_", "")}Config(AppConfig):
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
    class_name = entity.name

    lines = [
        f"class {class_name}(models.Model):",
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
            f'        return str(self.{_display_field(entity)})',
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

    suffix = ""

    if options:
        suffix = ", " + ", ".join(options)

    if field.type == FieldType.STRING:
        string_options = []

        if not field.required:
            string_options.append("blank=True")

        if field.default is not None:
            string_options.append(f"default={field.default!r}")

        suffix = (
            ", " + ", ".join(string_options)
            if string_options
            else ""
        )

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
            return f"models.CharField(max_length=255, choices=[{choices}], {', '.join(options)})"

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
            f"models.ForeignKey("
            f'"{field.entity}", '
            f"{', '.join(reference_options)}"
            f")"
        )

    raise ValueError(f"Unsupported field type: {field.type}")


def _admin_py(app_name: str) -> str:
    return "from django.contrib import admin\n"
