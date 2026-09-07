from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    REFERENCE = "reference"


class PageType(str, Enum):
    LIST = "list"
    CREATE = "create"
    EDIT = "edit"
    DETAIL = "detail"


@dataclass
class Field:
    name: str
    type: FieldType
    required: bool = False
    default: Any = None

    # ENUM
    values: list[str] = field(default_factory=list)

    # REFERENCE
    entity: str | None = None


@dataclass
class Entity:
    name: str
    fields: list[Field]


@dataclass
class Page:
    name: str
    route: str
    type: PageType
    entity: str


@dataclass
class Application:
    version: str
    name: str
    title: str
    entities: list[Entity]
    pages: list[Page]
