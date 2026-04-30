from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import tkinter as tk
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secure_random_password_generator.password_core import (  # noqa: E402
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    PasswordOptions,
    PasswordPolicyError,
    generate_password,
)
from secure_random_password_generator.secure_store import LocalEncryptedHistory, history_entry  # noqa: E402


class GuiSmokeTests(unittest.TestCase):
    def test_gui_can_initialize_and_close(self) -> None:
        app_dir = ROOT / "build" / "gui-test-app-dir"
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True)
        os.environ["SECURE_RANDOM_PASSWORD_APP_DIR"] = str(app_dir)
        from secure_random_password_generator.gui import BUTTON_COPY, BUTTON_GENERATE, FONT_EN, SecurePasswordApp

        app = SecurePasswordApp()
        try:
            app.update_idletasks()
            self.assertTrue(app.winfo_exists())
            self.assertEqual(app.title(), "安全密码生成器")
            self.assertIn(FONT_EN, app.password_text.cget("font"))
            self.assertIsInstance(app.length_entry, tk.Entry)
            self.assertEqual(app.password_display.cget("height"), 58)
            self.assertEqual(app.password_text.place_info().get("rely"), "0.5")
            self.assertEqual(app.copy_button.cget("text"), "复制密码")
            self.assertEqual(app.copy_button.cget("bg"), BUTTON_COPY)
            self.assertEqual(app.generate_button.cget("text"), "重新生成")
            self.assertEqual(app.generate_button.cget("bg"), BUTTON_GENERATE)
            self.assertFalse(any(isinstance(child, tk.Canvas) for child in app.winfo_children()))
        finally:
            app.destroy()
            os.environ.pop("SECURE_RANDOM_PASSWORD_APP_DIR", None)

    def test_gui_unique_mapping_is_shown_in_password_box_only(self) -> None:
        app_dir = ROOT / "build" / "gui-history-test-app-dir"
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True)
        os.environ["SECURE_RANDOM_PASSWORD_APP_DIR"] = str(app_dir)
        from secure_random_password_generator.gui import DANGER, SUCCESS, SecurePasswordApp

        app = SecurePasswordApp()
        try:
            self.assertEqual(app.current_password, "")
            self.assertEqual(app.password_status_var.get(), "输入字符串后生成密码")
            self.assertFalse(hasattr(app, "history_tree"))

            related_text = "邮箱账户"
            app.related_var.set(related_text)
            self.assertNotEqual(app.current_password, "")
            self.assertEqual(app.store.load(), [])
            self.assertIn("新随机密码", app.password_status_var.get())

            app.length_var.set("24")
            app.generate()
            self.assertEqual(app.length_var.get(), "24")
            self.assertEqual(len(app.current_password), 24)

            app.length_var.set("1")
            app.generate()
            self.assertEqual(app.length_var.get(), "4")
            self.assertEqual(len(app.current_password), 4)
            self.assertFalse(any(ch in app.current_password for ch in related_text))
            self.assertEqual(app.store.load(), [])
            self.assertEqual(app.password_text.cget("state"), "disabled")
            self.assertEqual(app.password_text.cget("wrap"), "none")
            password_text = app.password_text.get("1.0", "end-1c")
            self.assertEqual(password_text, app.current_password)
            tag_names = {
                tag
                for index in range(len(password_text))
                for tag in app.password_text.tag_names(f"1.{index}")
            }
            self.assertTrue(tag_names.intersection({"upper", "lower", "digit", "symbol"}))
            app.password_text.insert("end", "x")
            self.assertEqual(app.password_text.get("1.0", "end-1c"), password_text)
            app.clipboard_clear()
            app.password_text.tag_add("sel", "1.0", "end-1c")
            app.password_text.event_generate("<<Copy>>")
            app.update()
            with self.assertRaises(tk.TclError):
                app.clipboard_get()

            app.copy_password()
            entries = app.store.load()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["input_text"], related_text)
            saved_password = app.current_password
            self.assertIn("已复制并保存", app.password_status_var.get())
            self.assertEqual(app.password_status_label.cget("fg"), SUCCESS)

            app.related_var.set("")
            self.assertEqual(app.current_password, "")
            app.related_var.set(related_text)
            self.assertEqual(app.current_password, saved_password)
            self.assertEqual(app.password_text.get("1.0", "end-1c"), saved_password)
            self.assertIn("已保存记录", app.password_status_var.get())
            self.assertEqual(app.password_status_label.cget("fg"), DANGER)

            app.generate()
            updated_password = app.current_password
            app.copy_password()
            entries = app.store.load()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["password"], updated_password)
        finally:
            app.destroy()
            os.environ.pop("SECURE_RANDOM_PASSWORD_APP_DIR", None)


class PasswordCoreTests(unittest.TestCase):
    def test_default_password_is_strong_and_has_all_default_categories(self) -> None:
        result = generate_password()
        self.assertEqual(len(result.password), 16)
        self.assertGreaterEqual(result.entropy_bits, 100)
        self.assertTrue(any(ch in UPPERCASE for ch in result.password))
        self.assertTrue(any(ch in LOWERCASE for ch in result.password))
        self.assertTrue(any(ch in DIGITS for ch in result.password))
        self.assertTrue(any(ch in SYMBOLS for ch in result.password))

    def test_related_text_is_not_forced_into_password(self) -> None:
        related_text = "邮箱账户中文内容"
        result = generate_password(PasswordOptions(length=16, required_text=related_text))
        self.assertEqual(len(result.password), 16)
        self.assertFalse(any(ch in result.password for ch in related_text))

    def test_weak_digit_only_configuration_is_rejected_by_default_policy(self) -> None:
        with self.assertRaises(PasswordPolicyError):
            generate_password(
                PasswordOptions(
                    length=16,
                    include_uppercase=False,
                    include_lowercase=False,
                    include_symbols=False,
                )
            )

    def test_long_digit_only_configuration_is_allowed(self) -> None:
        result = generate_password(
            PasswordOptions(
                length=20,
                include_uppercase=False,
                include_lowercase=False,
                include_symbols=False,
            )
        )
        self.assertEqual(len(result.password), 20)
        self.assertTrue(all(ch in DIGITS for ch in result.password))


class StoreTests(unittest.TestCase):
    def test_encrypted_history_roundtrip(self) -> None:
        app_dir = ROOT / "build" / "test-app-dir"
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True)
        store = LocalEncryptedHistory(app_dir=app_dir)
        entry = history_entry(
            input_text="abc",
            password="abcDEF123!@#4567",
            length=16,
            categories=("uppercase", "lowercase", "digits", "symbols"),
            entropy_bits=101.4,
            charset_size=85,
        )
        store.append(entry)
        loaded = store.load()
        self.assertEqual(loaded[-1]["input_text"], "abc")
        self.assertEqual(loaded[-1]["password"], "abcDEF123!@#4567")
        raw = store.history_path.read_bytes()
        self.assertNotIn(b"abcDEF123", raw)
        self.assertTrue(store.key_path.exists())

    def test_upsert_unique_keeps_one_password_per_input(self) -> None:
        app_dir = ROOT / "build" / "test-upsert-app-dir"
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True)
        store = LocalEncryptedHistory(app_dir=app_dir)
        first = history_entry(
            input_text="abc",
            password="abcDEF123!@#4567",
            length=16,
            categories=("uppercase", "lowercase", "digits", "symbols"),
            entropy_bits=101.4,
            charset_size=85,
        )
        second = history_entry(
            input_text="abc",
            password="XYZdef987!@#6543",
            length=16,
            categories=("uppercase", "lowercase", "digits", "symbols"),
            entropy_bits=101.4,
            charset_size=85,
        )
        store.upsert_unique(first)
        store.upsert_unique(second)
        loaded = store.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["password"], "XYZdef987!@#6543")
        self.assertEqual(store.find_by_input("abc")["password"], "XYZdef987!@#6543")


if __name__ == "__main__":
    raise SystemExit(unittest.main(verbosity=2))
