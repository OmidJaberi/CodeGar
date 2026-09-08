import argparse
import sys

from codegar.generators.django import generate_django
from codegar.parser.json import ArchitectureParseError, parse_architecture_file
from codegar.validator.validate import ValidationError, validate_application


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="codegar",
        description="Compile declarative application architecture into software.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an architecture file.",
    )
    validate_parser.add_argument(
        "architecture",
        help="Path to architecture.json",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate an application from an architecture file.",
    )
    generate_parser.add_argument(
        "architecture",
        help="Path to architecture.json",
    )
    generate_parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Output directory (default: ./output)",
    )

    args = parser.parse_args()

    if args.command == "validate":
        return _validate(args.architecture)

    if args.command == "generate":
        return _generate(args.architecture, args.output)

    return 1


def _load_application(path: str):
    application = parse_architecture_file(path)
    validate_application(application)
    return application


def _validate(path: str) -> int:
    try:
        _load_application(path)
    except (ArchitectureParseError, ValidationError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print("Architecture is valid.")
    return 0


def _generate(path: str, output: str) -> int:
    try:
        application = _load_application(path)
        generate_django(application, output)
    except (ArchitectureParseError, ValidationError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Generated {application.title} in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
