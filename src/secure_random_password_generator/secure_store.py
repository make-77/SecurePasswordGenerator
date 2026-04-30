from __future__ import annotations

from datetime import datetime, timezone
import base64
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MAGIC = b"SPG1"
APP_DIR_ENV = "SECURE_RANDOM_PASSWORD_APP_DIR"
MAX_HISTORY_ITEMS = 500


class StorageError(RuntimeError):
    pass


def application_dir() -> Path:
    env_dir = os.environ.get(APP_DIR_ENV)
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _namespace() -> str:
    if hasattr(os, "getuid"):
        return f"u{os.getuid()}"
    user = re.sub(r"[^A-Za-z0-9_.-]+", "_", getpass.getuser() or "local")
    return f"user-{user}"


def storage_dir(app_dir: Path | None = None) -> Path:
    root = app_dir or application_dir()
    return root / "storage" / _namespace()


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o700 if path.is_dir() else 0o600)
    except OSError:
        pass


class LocalEncryptedHistory:
    def __init__(self, app_dir: Path | None = None) -> None:
        self.app_dir = app_dir or application_dir()
        self.storage_dir = storage_dir(self.app_dir)
        self.key_path = self.storage_dir / "app.key"
        self.history_path = self.storage_dir / "history.enc"

    def ensure_ready(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            _chmod_private(self.storage_dir)
        except OSError as exc:
            raise StorageError(f"软件目录不可写：{self.storage_dir}") from exc

    def _load_key(self) -> bytes:
        self.ensure_ready()
        if self.key_path.exists():
            try:
                raw = self.key_path.read_bytes()
                key = base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise StorageError("本地加密密钥损坏，无法读取历史。") from exc
            if len(key) != 32:
                raise StorageError("本地加密密钥长度不正确。")
            return key

        key = secrets.token_bytes(32)
        try:
            self.key_path.write_bytes(base64.b64encode(key))
            _chmod_private(self.key_path)
        except OSError as exc:
            raise StorageError(f"无法在软件目录创建加密密钥：{self.key_path}") from exc
        return key

    def load(self) -> list[dict[str, Any]]:
        self.ensure_ready()
        if not self.history_path.exists():
            return []
        key = self._load_key()
        raw = self.history_path.read_bytes()
        if len(raw) < len(MAGIC) + 12 or not raw.startswith(MAGIC):
            raise StorageError("历史文件格式无效。")
        nonce = raw[len(MAGIC) : len(MAGIC) + 12]
        ciphertext = raw[len(MAGIC) + 12 :]
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
            data = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise StorageError("历史文件解密失败。") from exc
        if not isinstance(data, list):
            raise StorageError("历史文件内容无效。")
        return data

    def save(self, entries: list[dict[str, Any]]) -> None:
        self.ensure_ready()
        key = self._load_key()
        clean_entries = entries[-MAX_HISTORY_ITEMS:]
        plaintext = json.dumps(clean_entries, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        payload = MAGIC + nonce + ciphertext
        temp_path = self.history_path.with_suffix(".enc.tmp")
        try:
            temp_path.write_bytes(payload)
            _chmod_private(temp_path)
            temp_path.replace(self.history_path)
            _chmod_private(self.history_path)
        except OSError as exc:
            raise StorageError(f"无法写入加密历史：{self.history_path}") from exc

    def append(self, entry: dict[str, Any]) -> None:
        entries = self.load()
        entries.append(entry)
        self.save(entries)

    def find_by_input(self, input_text: str) -> dict[str, Any] | None:
        for entry in reversed(self.load()):
            if entry.get("input_text") == input_text:
                return entry
        return None

    def upsert_unique(self, entry: dict[str, Any]) -> None:
        input_text = entry.get("input_text")
        entries = [item for item in self.load() if item.get("input_text") != input_text]
        entries.append(entry)
        self.save(entries)

    def clear(self) -> None:
        self.ensure_ready()
        for path in (self.history_path, self.history_path.with_suffix(".enc.tmp")):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise StorageError(f"无法清理历史文件：{path}") from exc


def history_entry(
    *,
    input_text: str,
    password: str,
    length: int,
    categories: tuple[str, ...],
    entropy_bits: float,
    charset_size: int,
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_text": input_text,
        "password": password,
        "length": length,
        "categories": list(categories),
        "entropy_bits": round(entropy_bits, 2),
        "charset_size": charset_size,
    }
