from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from . import __app_name__
from .password_core import (
    DEFAULT_LENGTH,
    MAX_LENGTH,
    MIN_LENGTH,
    PasswordOptions,
    PasswordPolicyError,
    generate_password,
    strength_label,
)
from .secure_store import LocalEncryptedHistory, StorageError, history_entry


BG = "#06111d"
PANEL = "#091725"
PANEL_ALT = "#0c1c2b"
INPUT = "#030b14"
BORDER = "#22364a"
BORDER_SOFT = "#17283a"
TEXT = "#f4f7fb"
MUTED = "#9aa8b8"
ACCENT = "#3b82ff"
ACCENT_LIGHT = "#78c7ff"
SUCCESS = "#35d68c"
YELLOW = "#ffd166"
DANGER = "#ff6b7a"
BUTTON_COPY = "#16a34a"
BUTTON_COPY_HOVER = "#1fc878"
BUTTON_GENERATE = "#2563eb"
BUTTON_GENERATE_HOVER = "#3b82f6"
BUTTON_SECONDARY = "#102236"
BUTTON_SECONDARY_HOVER = "#183653"

FONT_CN = "华文中宋"
FONT_EN = "Courier New"
FONT_UI = (FONT_CN, 10)
FONT_UI_BOLD = (FONT_CN, 10, "bold")
FONT_SECTION = (FONT_CN, 13, "bold")
FONT_MONO = (FONT_EN, 10)
FONT_MONO_BOLD = (FONT_EN, 13, "bold")
FONT_PASSWORD = (FONT_EN, 21, "bold")


def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative_path
    return Path(__file__).resolve().parents[2] / relative_path


class SecurePasswordApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(__app_name__)
        self.geometry("1360x700")
        self.minsize(1180, 660)
        self.configure(bg=BG)
        self._set_window_icon()

        self.store = LocalEncryptedHistory()
        self.current_password = ""
        self.current_length = DEFAULT_LENGTH
        self.current_categories: tuple[str, ...] = ()
        self.current_entropy_bits = 0.0
        self.current_charset_size = 0
        self._clipboard_after_id: str | None = None

        self.length_var = tk.StringVar(value=str(DEFAULT_LENGTH))
        self.related_var = tk.StringVar()
        self.related_count_var = tk.StringVar(value="0/200")
        self.upper_var = tk.BooleanVar(value=True)
        self.lower_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.strength_var = tk.StringVar(value="未生成")
        self.password_status_var = tk.StringVar(value="输入字符串后生成密码")

        self.related_var.trace_add("write", self._update_related_count)

        self._configure_style()
        self._build_layout()
        self._sync_password_for_related_text()

    def _set_window_icon(self) -> None:
        icon_path = resource_path("assets/secure-random-password-generator.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar", background=SUCCESS, troughcolor="#122236", bordercolor=BORDER)

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_main()
        self._build_footer()

    def _build_main(self) -> None:
        main = tk.Frame(self, bg=BG)
        main.grid(row=0, column=0, sticky="nsew", padx=18, pady=(18, 10))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self._build_generate_panel(main).grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self._build_password_panel(main).grid(row=1, column=0, sticky="nsew")

    def _panel(self, parent: tk.Widget) -> tk.Frame:
        panel = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.grid_columnconfigure(0, weight=1)
        return panel

    def _build_generate_panel(self, parent: tk.Widget) -> tk.Frame:
        panel = self._panel(parent)
        tk.Label(panel, text="生成新密码", bg=PANEL, fg=TEXT, font=FONT_SECTION).grid(
            row=0, column=0, sticky="w", padx=22, pady=(18, 14)
        )
        self._separator(panel).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(panel, bg=PANEL)
        body.grid(row=2, column=0, sticky="ew", padx=22, pady=18)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)

        tk.Label(body, text="输入与密码相关的内容", bg=PANEL, fg=TEXT, font=FONT_UI_BOLD).grid(
            row=0, column=0, sticky="w"
        )
        input_wrap = tk.Frame(body, bg=INPUT, highlightbackground=ACCENT, highlightthickness=1)
        input_wrap.grid(row=1, column=0, sticky="ew", pady=(10, 18))
        input_wrap.grid_columnconfigure(0, weight=1)
        related_entry = tk.Entry(
            input_wrap,
            textvariable=self.related_var,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=FONT_UI,
        )
        related_entry.grid(row=0, column=0, sticky="ew", ipady=11, padx=(14, 8))
        tk.Label(input_wrap, textvariable=self.related_count_var, bg=INPUT, fg=MUTED, font=FONT_MONO).grid(
            row=0, column=1, padx=(0, 12)
        )

        tk.Label(
            body,
            text="输入内容只用于建立本地加密对应关系；密码由安全随机源生成，不从输入内容推导。",
            bg=PANEL,
            fg=MUTED,
            wraplength=380,
            justify="left",
            font=FONT_UI,
        ).grid(row=1, column=1, sticky="nw", padx=(24, 0), pady=(10, 0))

        controls = tk.Frame(body, bg=PANEL)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew")
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(2, weight=1)

        self._build_length_block(controls).grid(row=0, column=0, sticky="nw")
        self._build_charset_block(controls).grid(row=0, column=1, sticky="nw", padx=(30, 20))
        self._build_strength_card(controls).grid(row=0, column=2, sticky="nsew")
        return panel

    def _build_length_block(self, parent: tk.Widget) -> tk.Frame:
        block = tk.Frame(parent, bg=PANEL)
        tk.Label(block, text="密码长度", bg=PANEL, fg=TEXT, font=FONT_UI_BOLD).pack(anchor="w", pady=(0, 10))
        row = tk.Frame(block, bg=PANEL)
        row.pack(anchor="w")
        self._button(row, "-", lambda: self._adjust_length(-1), width=44).pack(side="left")
        self.length_entry = tk.Entry(
            row,
            textvariable=self.length_var,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            justify="center",
            relief="flat",
            width=8,
            font=FONT_MONO_BOLD,
        )
        self.length_entry.pack(side="left", ipady=10)
        self.length_entry.bind("<FocusOut>", lambda _event: self._normalize_length())
        self.length_entry.bind("<Return>", lambda _event: self._normalize_length())
        self._button(row, "+", lambda: self._adjust_length(1), width=44).pack(side="left")
        tk.Label(block, text=f"建议长度：{MIN_LENGTH}-{MAX_LENGTH}，默认 16", bg=PANEL, fg=MUTED, font=FONT_UI).pack(
            anchor="w", pady=(10, 0)
        )
        return block

    def _build_charset_block(self, parent: tk.Widget) -> tk.Frame:
        block = tk.Frame(parent, bg=PANEL)
        tk.Label(block, text="字符集", bg=PANEL, fg=TEXT, font=FONT_UI_BOLD).pack(anchor="w", pady=(0, 8))
        for text, var in (
            ("大写字母 (A-Z)", self.upper_var),
            ("小写字母 (a-z)", self.lower_var),
            ("数字 (0-9)", self.digits_var),
            ("特殊字符 (!@#$%^&*)", self.symbols_var),
        ):
            tk.Checkbutton(
                block,
                text=text,
                variable=var,
                bg=PANEL,
                fg=TEXT,
                selectcolor=ACCENT,
                activebackground=PANEL,
                activeforeground=TEXT,
                font=FONT_UI,
                relief="flat",
            ).pack(anchor="w", pady=2)
        return block

    def _build_strength_card(self, parent: tk.Widget) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL_ALT, highlightbackground=BORDER, highlightthickness=1)
        card.grid_columnconfigure(0, weight=1)
        tk.Label(card, text="强度", bg=PANEL_ALT, fg=TEXT, font=FONT_UI_BOLD).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        status = tk.Frame(card, bg=PANEL_ALT)
        status.grid(row=1, column=0, sticky="ew", padx=18)
        tk.Label(status, text="✓", bg=SUCCESS, fg="white", width=2, height=1, font=(FONT_CN, 15, "bold")).pack(
            side="left"
        )
        tk.Label(status, textvariable=self.strength_var, bg=PANEL_ALT, fg=SUCCESS, font=(FONT_CN, 18, "bold")).pack(
            side="left", padx=(12, 0)
        )
        self.strength_bar = ttk.Progressbar(card, maximum=120, value=0)
        self.strength_bar.grid(row=2, column=0, sticky="ew", padx=18, pady=(14, 12))
        tk.Label(
            card,
            text="基于随机性、长度和字符集复杂度评估。",
            bg=PANEL_ALT,
            fg=MUTED,
            font=FONT_UI,
        ).grid(row=3, column=0, sticky="w", padx=18, pady=(0, 16))
        return card

    def _build_password_panel(self, parent: tk.Widget) -> tk.Frame:
        panel = self._panel(parent)
        panel.grid_rowconfigure(1, weight=1)
        tk.Label(panel, text="生成的密码", bg=PANEL, fg=TEXT, font=FONT_SECTION).grid(
            row=0, column=0, sticky="w", padx=22, pady=(18, 8)
        )

        row = tk.Frame(panel, bg=PANEL)
        row.grid(row=1, column=0, sticky="ew", padx=22, pady=(6, 10))
        row.grid_columnconfigure(0, weight=1)
        self.password_display = tk.Frame(row, bg=INPUT, height=58, highlightthickness=0)
        self.password_display.grid(row=0, column=0, sticky="ew")
        self.password_display.grid_propagate(False)
        self.password_display.grid_columnconfigure(0, weight=1)
        self.password_display.grid_rowconfigure(0, weight=1)
        self.password_text = tk.Text(
            self.password_display,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground="#24496e",
            selectforeground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            height=1,
            wrap="none",
            font=FONT_PASSWORD,
            cursor="xterm",
            undo=False,
            autoseparators=False,
            exportselection=False,
            padx=0,
            pady=0,
        )
        self.password_text.place(x=18, rely=0.5, anchor="w", relwidth=1.0, width=-36, height=38)
        self._configure_password_text()
        self.copy_button = self._button(row, "复制密码", self.copy_password, width=120, variant="copy")
        self.copy_button.grid(row=0, column=1, padx=(16, 8), ipady=9)
        self.generate_button = self._button(row, "重新生成", self.generate, width=136, variant="generate")
        self.generate_button.grid(row=0, column=2, ipady=9)

        self.password_status_label = tk.Label(
            panel,
            textvariable=self.password_status_var,
            bg=PANEL,
            fg=MUTED,
            font=FONT_UI,
            anchor="w",
        )
        self.password_status_label.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 18))
        return panel

    def _configure_password_text(self) -> None:
        self.password_text.tag_configure("upper", foreground="#f5f7fb")
        self.password_text.tag_configure("lower", foreground=ACCENT_LIGHT)
        self.password_text.tag_configure("digit", foreground=YELLOW)
        self.password_text.tag_configure("symbol", foreground="#ff7c93")
        for sequence in (
            "<Control-c>",
            "<Control-C>",
            "<Control-Insert>",
            "<<Copy>>",
            "<<Cut>>",
            "<<Paste>>",
            "<Button-3>",
        ):
            self.password_text.bind(sequence, lambda _event: "break")
        self.password_text.configure(state="disabled")

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=BG, height=34)
        footer.grid(row=1, column=0, sticky="ew")
        tk.Label(
            footer,
            text="所有操作在本地完成  •  使用加密存储  •  不在系统中残留任何数据",
            bg=BG,
            fg=MUTED,
            font=FONT_UI,
        ).pack(anchor="center", pady=(0, 12))

    def _separator(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, bg=BORDER_SOFT, height=1)

    def _button(self, parent: tk.Widget, text: str, command, width: int = 118, variant: str = "secondary") -> tk.Button:
        colors = {
            "copy": (BUTTON_COPY, BUTTON_COPY_HOVER),
            "generate": (BUTTON_GENERATE, BUTTON_GENERATE_HOVER),
            "secondary": (BUTTON_SECONDARY, BUTTON_SECONDARY_HOVER),
        }
        bg, active_bg = colors.get(variant, colors["secondary"])
        button = tk.Button(
            parent,
            text=text,
            command=command,
            width=max(3, width // 12),
            bg=bg,
            fg=TEXT,
            activebackground=active_bg,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            font=(FONT_CN, 11, "bold"),
            cursor="hand2",
        )
        button.bind("<Enter>", lambda _event: button.configure(bg=active_bg))
        button.bind("<Leave>", lambda _event: button.configure(bg=bg))
        return button

    def _update_related_count(self, *_args) -> None:
        value = self.related_var.get()
        if len(value) > 200:
            self.related_var.set(value[:200])
            value = self.related_var.get()
        self.related_count_var.set(f"{len(value)}/200")
        self._sync_password_for_related_text()

    def _length_value(self) -> int:
        try:
            return int(self.length_var.get())
        except (TypeError, ValueError):
            return DEFAULT_LENGTH

    def _normalize_length(self) -> int:
        value = max(MIN_LENGTH, min(MAX_LENGTH, self._length_value()))
        self.length_var.set(str(value))
        return value

    def _password_options(self) -> PasswordOptions:
        return PasswordOptions(
            length=self._normalize_length(),
            required_text=self._related_key(),
            include_uppercase=self.upper_var.get(),
            include_lowercase=self.lower_var.get(),
            include_digits=self.digits_var.get(),
            include_symbols=self.symbols_var.get(),
            min_entropy_bits=0.0,
        )

    def _adjust_length(self, delta: int) -> None:
        value = max(MIN_LENGTH, min(MAX_LENGTH, self._length_value() + delta))
        self.length_var.set(str(value))

    def _password_tag(self, char: str) -> str:
        if char.isdigit():
            return "digit"
        if char.isupper():
            return "upper"
        if char.islower():
            return "lower"
        return "symbol"

    def _related_key(self) -> str:
        return self.related_var.get().strip()

    def _set_password_status(self, text: str, color: str = MUTED) -> None:
        self.password_status_var.set(text)
        if hasattr(self, "password_status_label"):
            self.password_status_label.configure(fg=color)

    def _render_password(self, password: str) -> None:
        self.password_text.configure(state="normal")
        self.password_text.delete("1.0", "end")
        for char in password:
            self.password_text.insert("end", char, self._password_tag(char))
        self.password_text.configure(state="disabled")
        self.password_text.xview_moveto(0)

    def _clear_password(self) -> None:
        self.current_password = ""
        self.current_length = self._length_value()
        self.current_categories = ()
        self.current_entropy_bits = 0.0
        self.current_charset_size = 0
        self._render_password("")
        self.strength_var.set("未生成")
        self.strength_bar.configure(value=0)
        self._set_password_status("输入字符串后生成密码", MUTED)

    def _apply_stored_entry(self, entry: dict[str, object]) -> None:
        password = str(entry.get("password", ""))
        self.current_password = password
        self.current_length = int(entry.get("length", self._length_value()) or self._length_value())
        self.current_categories = tuple(str(item) for item in entry.get("categories", ()) or ())
        self.current_entropy_bits = float(entry.get("entropy_bits", 0) or 0)
        self.current_charset_size = int(entry.get("charset_size", 0) or 0)
        self._render_password(password)
        entropy = self.current_entropy_bits
        self.strength_var.set(strength_label(entropy) if entropy else "已保存")
        self.strength_bar.configure(value=min(120, entropy))
        self._set_password_status("已保存记录：当前字符串对应唯一密码", DANGER)

    def _sync_password_for_related_text(self) -> None:
        if not hasattr(self, "password_text"):
            return
        key = self._related_key()
        if not key:
            self._clear_password()
            return
        try:
            entry = self.store.find_by_input(key)
            if entry:
                self._apply_stored_entry(entry)
            else:
                self._generate_candidate(save=False)
        except (PasswordPolicyError, StorageError, ValueError) as exc:
            self._clear_password()
            messagebox.showerror("无法生成安全密码", str(exc), parent=self)

    def _generate_candidate(self, *, save: bool) -> None:
        key = self._related_key()
        if not key:
            self._clear_password()
            return
        options = self._password_options()
        result = generate_password(options)
        self.current_password = result.password
        self.current_length = options.length
        self.current_categories = result.categories
        self.current_entropy_bits = result.entropy_bits
        self.current_charset_size = result.charset_size
        self._render_password(result.password)
        self.strength_var.set(strength_label(result.entropy_bits))
        self.strength_bar.configure(value=min(120, result.entropy_bits))
        self._set_password_status("新随机密码：点击复制后保存为当前字符串的唯一记录", MUTED)
        if save:
            self._save_current_mapping(status="已保存记录：当前字符串对应唯一密码")

    def generate(self) -> None:
        try:
            self._generate_candidate(save=False)
        except (PasswordPolicyError, StorageError, ValueError) as exc:
            messagebox.showerror("无法生成安全密码", str(exc), parent=self)

    def copy_password(self) -> None:
        key = self._related_key()
        if not key:
            messagebox.showinfo("无法复制", "请先输入与密码相关的字符串。", parent=self)
            return
        if not self.current_password:
            self._generate_candidate(save=False)
        if not self.current_password:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current_password)
        self._save_current_mapping(status="已复制并保存：当前字符串对应唯一密码")
        if self._clipboard_after_id:
            self.after_cancel(self._clipboard_after_id)
        self._clipboard_after_id = self.after(30_000, self._clear_clipboard_if_unchanged, self.current_password)

    def _save_current_mapping(self, *, status: str) -> None:
        key = self._related_key()
        if not key or not self.current_password:
            return
        self.store.upsert_unique(
            history_entry(
                input_text=key,
                password=self.current_password,
                length=self.current_length,
                categories=self.current_categories,
                entropy_bits=self.current_entropy_bits,
                charset_size=self.current_charset_size,
            )
        )
        self._set_password_status(status, SUCCESS if "复制" in status else MUTED)

    def _clear_clipboard_if_unchanged(self, expected: str) -> None:
        try:
            if self.clipboard_get() == expected:
                self.clipboard_clear()
        except tk.TclError:
            pass
        self._clipboard_after_id = None


def run_gui() -> int:
    app = SecurePasswordApp()
    app.mainloop()
    return 0
