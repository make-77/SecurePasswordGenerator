from __future__ import annotations

import argparse
import io
from pathlib import Path
import tarfile
import time


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "secure-random-password-generator"
VERSION = "1.0.0"


def tar_add_bytes(tar: tarfile.TarFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))


def tar_add_dir(tar: tarfile.TarFile, name: str, mode: int = 0o755) -> None:
    info = tarfile.TarInfo(name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.mtime = int(time.time())
    tar.addfile(info)


def make_control_tar() -> bytes:
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-tk, python3-cryptography
Maintainer: make-77 <make-77@users.noreply.github.com>
Description: Secure random password generator
 A local desktop tool that creates cryptographically strong passwords and stores
 encrypted mappings only in its software directory.
"""
    postinst = """#!/bin/sh
set -e
mkdir -p /opt/secure-random-password-generator/storage
chmod 1777 /opt/secure-random-password-generator/storage
exit 0
"""
    postrm = """#!/bin/sh
set -e
if [ "$1" = "purge" ]; then
  rm -rf /opt/secure-random-password-generator/storage
fi
exit 0
"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar_add_bytes(tar, "./control", control.encode("utf-8"))
        tar_add_bytes(tar, "./postinst", postinst.encode("utf-8"), 0o755)
        tar_add_bytes(tar, "./postrm", postrm.encode("utf-8"), 0o755)
    return buffer.getvalue()


def iter_source_files() -> list[Path]:
    paths = [ROOT / "main.py", ROOT / "README.md"]
    paths.extend(sorted((ROOT / "src" / "secure_random_password_generator").glob("*.py")))
    paths.append(ROOT / "assets" / "secure-random-password-generator.svg")
    return paths


def make_data_tar() -> bytes:
    launcher = """#!/bin/sh
export SECURE_RANDOM_PASSWORD_APP_DIR=/opt/secure-random-password-generator
export PYTHONPATH=/opt/secure-random-password-generator/src${PYTHONPATH:+:$PYTHONPATH}
exec python3 /opt/secure-random-password-generator/main.py "$@"
"""
    desktop = """[Desktop Entry]
Type=Application
Name=Secure Password Generator
Name[zh_CN]=安全密码生成器
Comment=Generate secure random passwords locally
Comment[zh_CN]=在本地生成安全随机密码
Exec=secure-random-password-generator
Icon=secure-random-password-generator
Terminal=false
Categories=Utility;Security;
"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar_add_dir(tar, "./opt")
        tar_add_dir(tar, "./opt/secure-random-password-generator")
        tar_add_dir(tar, "./opt/secure-random-password-generator/src")
        tar_add_dir(tar, "./opt/secure-random-password-generator/src/secure_random_password_generator")
        tar_add_dir(tar, "./opt/secure-random-password-generator/assets")
        tar_add_dir(tar, "./opt/secure-random-password-generator/storage", 0o1777)
        tar_add_dir(tar, "./usr")
        tar_add_dir(tar, "./usr/bin")
        tar_add_dir(tar, "./usr/share")
        tar_add_dir(tar, "./usr/share/applications")
        tar_add_dir(tar, "./usr/share/icons")
        tar_add_dir(tar, "./usr/share/icons/hicolor")
        tar_add_dir(tar, "./usr/share/icons/hicolor/scalable")
        tar_add_dir(tar, "./usr/share/icons/hicolor/scalable/apps")

        for src in iter_source_files():
            rel = src.relative_to(ROOT).as_posix()
            target = f"./opt/secure-random-password-generator/{rel}"
            tar_add_bytes(tar, target, src.read_bytes(), 0o644)

        icon = (ROOT / "assets" / "secure-random-password-generator.svg").read_bytes()
        tar_add_bytes(
            tar,
            "./usr/share/icons/hicolor/scalable/apps/secure-random-password-generator.svg",
            icon,
            0o644,
        )
        tar_add_bytes(tar, "./usr/bin/secure-random-password-generator", launcher.encode("utf-8"), 0o755)
        tar_add_bytes(tar, "./usr/share/applications/secure-random-password-generator.desktop", desktop.encode("utf-8"), 0o644)
    return buffer.getvalue()


def ar_member(name: str, data: bytes) -> bytes:
    encoded_name = (name + "/").encode("ascii")
    if len(encoded_name) > 16:
        raise ValueError(f"ar member name too long: {name}")
    header = (
        encoded_name.ljust(16, b" ")
        + str(int(time.time())).encode("ascii").ljust(12, b" ")
        + b"0     "
        + b"0     "
        + b"100644  "
        + str(len(data)).encode("ascii").ljust(10, b" ")
        + b"`\n"
    )
    if len(data) % 2:
        data += b"\n"
    return header + data


def build(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    deb_path = output_dir / f"{PACKAGE}_{VERSION}_all.deb"
    content = b"!<arch>\n"
    content += ar_member("debian-binary", b"2.0\n")
    content += ar_member("control.tar.gz", make_control_tar())
    content += ar_member("data.tar.gz", make_data_tar())
    deb_path.write_bytes(content)
    return deb_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "dist"))
    args = parser.parse_args()
    deb_path = build(Path(args.output_dir))
    print(deb_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
