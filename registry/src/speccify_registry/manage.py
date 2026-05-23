"""`manage.py` equivalent exposed as a console script (`speccify-registry-manage`)."""

from __future__ import annotations

import os
import sys


def main(argv: list[str] | None = None) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "speccify_registry.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    main()
