import argparse
import sys

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

    args = parser.parse_args()

    if args.command == "validate":
        return _validate(args.architecture)

    return 1


def _validate(path: str) -> int:
    try:
        application = parse_architecture_file(path)
        validate_application(application)
    except (ArchitectureParseError, ValidationError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print("Architecture is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
