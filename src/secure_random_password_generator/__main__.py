from __future__ import annotations

import sys

from .cli import run_cli
from .gui import run_gui


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
