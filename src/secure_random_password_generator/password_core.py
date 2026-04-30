from __future__ import annotations

from dataclasses import dataclass
import math
import secrets
import string


UPPERCASE = string.ascii_uppercase
LOWERCASE = string.ascii_lowercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?"
DEFAULT_LENGTH = 16
MIN_LENGTH = 4
MAX_LENGTH = 128
MIN_ENTROPY_BITS = 60.0


class PasswordPolicyError(ValueError):
    """Raised when a requested password configuration is too weak or invalid."""


@dataclass(frozen=True)
class PasswordOptions:
    length: int = DEFAULT_LENGTH
    required_text: str = ""
    include_uppercase: bool = True
    include_lowercase: bool = True
    include_digits: bool = True
    include_symbols: bool = True
    custom_charset: str = ""
    use_custom_only: bool = False
    min_entropy_bits: float = MIN_ENTROPY_BITS


@dataclass(frozen=True)
class PasswordResult:
    password: str
    entropy_bits: float
    charset_size: int
    categories: tuple[str, ...]


def unique_chars(value: str) -> str:
    return "".join(dict.fromkeys(value))


def _reject_control_chars(label: str, value: str) -> None:
    bad = [ch for ch in value if ord(ch) < 32 or ord(ch) == 127]
    if bad:
        raise PasswordPolicyError(f"{label}不能包含控制字符。")


def _selected_groups(options: PasswordOptions) -> list[tuple[str, str]]:
    groups: list[tuple[str, str]] = []
    if options.include_uppercase:
        groups.append(("大写字母", UPPERCASE))
    if options.include_lowercase:
        groups.append(("小写字母", LOWERCASE))
    if options.include_digits:
        groups.append(("数字", DIGITS))
    if options.include_symbols:
        groups.append(("特殊字符", SYMBOLS))
    return groups


def build_charset(options: PasswordOptions) -> tuple[str, list[tuple[str, str]], tuple[str, ...]]:
    _reject_control_chars("相关内容", options.required_text)
    _reject_control_chars("自定义字符集", options.custom_charset)

    custom = unique_chars(options.custom_charset)
    if options.use_custom_only:
        if not custom:
            raise PasswordPolicyError("使用自定义字符集时，字符集不能为空。")
        pool = custom
        groups: list[tuple[str, str]] = []
        category_names = ("自定义字符集",)
    else:
        groups = _selected_groups(options)
        pool = unique_chars("".join(chars for _, chars in groups) + custom)
        category_names = tuple(name for name, _ in groups)
        if custom:
            category_names += ("自定义字符集",)

    if not pool:
        raise PasswordPolicyError("至少选择一种字符集。")
    if len(pool) < 2:
        raise PasswordPolicyError("字符集至少需要 2 个不同字符。")

    return pool, groups, category_names


def estimate_entropy_bits(length: int, charset_size: int) -> float:
    return length * math.log2(charset_size)


def validate_options(options: PasswordOptions) -> tuple[str, list[tuple[str, str]], tuple[str, ...], float]:
    if options.length < MIN_LENGTH or options.length > MAX_LENGTH:
        raise PasswordPolicyError(f"密码长度必须在 {MIN_LENGTH}-{MAX_LENGTH} 之间。")
    _reject_control_chars("相关内容", options.required_text)

    pool, groups, categories = build_charset(options)

    mandatory_count = len(groups)
    if mandatory_count > options.length:
        raise PasswordPolicyError("密码长度小于已选择字符集数量，无法包含所有选定类型。")

    entropy_bits = estimate_entropy_bits(options.length, len(pool))
    if entropy_bits < options.min_entropy_bits:
        raise PasswordPolicyError(
            f"当前配置强度仅 {entropy_bits:.1f} bit，低于 {options.min_entropy_bits:.0f} bit 的安全要求。"
        )

    return pool, groups, categories, entropy_bits


def generate_password(options: PasswordOptions | None = None) -> PasswordResult:
    options = options or PasswordOptions()
    pool, groups, categories, entropy_bits = validate_options(options)

    password_chars: list[str] = []

    for _, group_chars in groups:
        if not any(ch in group_chars for ch in password_chars):
            password_chars.append(secrets.choice(group_chars))

    while len(password_chars) < options.length:
        password_chars.append(secrets.choice(pool))

    secrets.SystemRandom().shuffle(password_chars)
    password = "".join(password_chars)
    return PasswordResult(
        password=password,
        entropy_bits=entropy_bits,
        charset_size=len(pool),
        categories=categories,
    )


def strength_label(entropy_bits: float) -> str:
    if entropy_bits >= 100:
        return "非常强"
    if entropy_bits >= 80:
        return "强"
    if entropy_bits >= MIN_ENTROPY_BITS:
        return "中等"
    return "弱"
