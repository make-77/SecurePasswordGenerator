from __future__ import annotations

import argparse
import sys

from .password_core import PasswordOptions, PasswordPolicyError, generate_password
from .secure_store import LocalEncryptedHistory, StorageError, history_entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secure-random-password-generator",
        description="Generate one secure password and print only the password.",
    )
    parser.add_argument("--length", "-l", type=int, default=16)
    parser.add_argument("--text", "-t", default="", help="Related label saved with history; it is not used to derive the password.")
    parser.add_argument("--charset", default="", help="Use this exact custom character set.")
    parser.add_argument("--extra-chars", default="", help="Append these characters to selected built-in sets.")
    parser.add_argument("--no-uppercase", action="store_true")
    parser.add_argument("--no-lowercase", action="store_true")
    parser.add_argument("--no-digits", action="store_true")
    parser.add_argument("--no-symbols", action="store_true")
    parser.add_argument("--min-entropy", type=float, default=60.0)
    parser.add_argument("--no-history", action="store_true")
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    use_custom_only = bool(args.charset)
    options = PasswordOptions(
        length=args.length,
        required_text=args.text,
        include_uppercase=not args.no_uppercase and not use_custom_only,
        include_lowercase=not args.no_lowercase and not use_custom_only,
        include_digits=not args.no_digits and not use_custom_only,
        include_symbols=not args.no_symbols and not use_custom_only,
        custom_charset=args.charset or args.extra_chars,
        use_custom_only=use_custom_only,
        min_entropy_bits=args.min_entropy,
    )

    try:
        result = generate_password(options)
        if not args.no_history:
            LocalEncryptedHistory().append(
                history_entry(
                    input_text=args.text,
                    password=result.password,
                    length=args.length,
                    categories=result.categories,
                    entropy_bits=result.entropy_bits,
                    charset_size=result.charset_size,
                )
            )
    except (PasswordPolicyError, StorageError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    sys.stdout.write(result.password + "\n")
    return 0
