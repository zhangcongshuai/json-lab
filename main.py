# -*- coding: utf-8 -*-
"""JSON Lab — JSON 格式化 & 时间戳转换（Windows 桌面）

视觉参考：VS Code / DevToys / Code Beautify
- 深色开发者主题
- JSON 语法高亮
- 行号 + 缩进参考线
- 结构树视图
"""

from __future__ import annotations

import json
import re
import sys
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import messagebox, ttk

APP_TITLE = "JSON Lab"
APP_SUB = "JSON 格式化 · 时间戳转换"
APP_VERSION = "2.0.0"
CST = timezone(timedelta(hours=8), name="CST")

# tkinter font tuples: (family, size, *styles) — no CSS-style fallback lists
def _pick_font(preferred: list[str], fallback: str) -> str:
    import tkinter.font as tkfont

    families = set(tkfont.families())
    for name in preferred:
        if name in families:
            return name
    return fallback


_UI_FAMILY = None
_MONO_FAMILY = None

def _init_fonts() -> None:
    global _UI_FAMILY, _MONO_FAMILY
    if _UI_FAMILY is None:
        _UI_FAMILY = _pick_font(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"], "Segoe UI")
    if _MONO_FAMILY is None:
        _MONO_FAMILY = _pick_font(["Cascadia Code", "Cascadia Mono", "Consolas", "Courier New"], "Consolas")

def _fonts():
    _init_fonts()
    return _UI_FAMILY, _MONO_FAMILY

# placeholder — resolved lazily via _fonts() when building widgets
UI_STACK = None
UI_SM = None
UI_TITLE = None
UI_NUM = None
UI_BTN = None
MONO_STACK = None


def ensure_fonts() -> None:
    global UI_STACK, UI_SM, UI_TITLE, UI_NUM, UI_BTN, MONO_STACK
    ui, mono = _fonts()
    UI_STACK = (ui, 10)
    UI_SM = (ui, 9)
    UI_TITLE = (ui, 13, "bold")
    UI_NUM = (mono, 14, "bold")
    UI_BTN = (ui, 10)
    MONO_STACK = (mono, 12)

THEMES = {
    "dark": {
        "name": "深色",
        "chrome": "#0D1117",
        "editor": "#161B22",
        "panel": "#21262D",
        "panel2": "#161B22",
        "border": "#30363D",
        "ink": "#E6EDF3",
        "muted": "#8B949E",
        "dim": "#484F58",
        "accent": "#2F81F7",
        "accent_hover": "#388BFD",
        "accent_soft": "#1F3A5F",
        "ok": "#3FB950",
        "err": "#F85149",
        "field": "#0D1117",
        "key": "#79C0FF",
        "string": "#3FB950",
        "number": "#FFA657",
        "bool": "#FF7B72",
        "null": "#FF7B72",
        "punct": "#8B949E",
        "guide": "#3D444D",
        "lineno": "#484F58",
        "current": "#21262D",
        "selection": "#264F78",
        "tree_sel": "#1F3A5F",
        "chip_bg": "#21262D",
        "chip_fg": "#C9D1D9",
        "input_bg": "#0D1117",
        "success_chip": "#238636",
        "warn_chip": "#9E6A03",
        "sb_thumb": "#6E7681",
        "sash": "#30363D",
    },
    "light": {
        "name": "浅色",
        "chrome": "#F6F8FA",
        "editor": "#FFFFFF",
        "panel": "#FFFFFF",
        "panel2": "#F6F8FA",
        "border": "#D0D7DE",
        "ink": "#1F2328",
        "muted": "#656D76",
        "dim": "#8C959F",
        "accent": "#0969DA",
        "accent_hover": "#0550AE",
        "accent_soft": "#D0E3F7",
        "ok": "#1A7F37",
        "err": "#CF222E",
        "field": "#FFFFFF",
        "key": "#0550AE",
        "string": "#0A3069",
        "number": "#953800",
        "bool": "#CF222E",
        "null": "#CF222E",
        "punct": "#656D76",
        "guide": "#D0D7DE",
        "lineno": "#8C959F",
        "current": "#F6F8FA",
        "selection": "#B6E3FF",
        "tree_sel": "#D0E3F7",
        "chip_bg": "#F6F8FA",
        "chip_fg": "#24292F",
        "input_bg": "#FFFFFF",
        "success_chip": "#1A7F37",
        "warn_chip": "#9A6700",
        "sb_thumb": "#8C959F",
        "sash": "#D0D7DE",
    },
}


# ---------- time / json core ----------

def now_dt() -> datetime:
    return datetime.now().astimezone()


def detect_ts_unit(value: float) -> str:
    av = abs(int(value)) if float(value).is_integer() else abs(value)
    digits = len(str(int(av))) if av >= 1 else 1
    if digits >= 16:
        return "μs"
    if digits >= 13:
        return "ms"
    return "s"


def ts_to_dt(value: float, unit: str) -> datetime:
    if unit == "ms":
        seconds = value / 1000.0
    elif unit == "μs":
        seconds = value / 1_000_000.0
    else:
        seconds = value
    if abs(seconds) > 32503680000:
        raise ValueError("时间戳超出可解析范围")
    return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone()


def dt_to_ts(dt: datetime, unit: str) -> int:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    seconds = dt.timestamp()
    if unit == "ms":
        return int(round(seconds * 1000))
    if unit == "μs":
        return int(round(seconds * 1_000_000))
    return int(round(seconds))


def parse_human_time(text: str) -> datetime:
    text = text.strip()
    if not text:
        raise ValueError("请输入日期时间")
    candidate = text.replace("Z", "+00:00").replace("z", "+00:00")
    formats = (
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d%H%M%S",
        "%Y%m%d",
    )
    try:
        dt = datetime.fromisoformat(candidate)
        return dt if dt.tzinfo is not None else dt.astimezone()
    except ValueError:
        pass
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).astimezone()
        except ValueError:
            continue
    raise ValueError("无法识别的时间格式，例如: 2026-09-20 12:30:00")


def format_json_text(raw: str, indent: int | str) -> str:
    return json.dumps(json.loads(raw), ensure_ascii=False, indent=indent, sort_keys=False)


def minify_json_text(raw: str) -> str:
    return json.dumps(json.loads(raw), ensure_ascii=False, separators=(",", ":"))


def json_preview(value, limit: int = 42) -> str:
    if isinstance(value, (dict, list)):
        kind = "object" if isinstance(value, dict) else "array"
        n = len(value)
        return f"{kind} · {n} 项"
    s = json.dumps(value, ensure_ascii=False)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _strip_json_strings(line: str) -> str:
    """Remove string literals so braces inside strings are ignored."""
    out = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == '"':
            i += 1
            while i < n:
                if line[i] == "\\":
                    i += 2
                    continue
                if line[i] == '"':
                    i += 1
                    break
                i += 1
            out.append('""')
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def analyze_json_folds(pretty: str) -> dict[int, int]:
    """Map opening line (1-based) -> closing line for multi-line { } / [ ] blocks."""
    folds: dict[int, int] = {}
    stack: list[int] = []
    for i, line in enumerate(pretty.split("\n"), start=1):
        code = _strip_json_strings(line)
        for ch in code:
            if ch in "{[":
                stack.append(i)
            elif ch in "}]":
                if stack:
                    start = stack.pop()
                    if i > start:
                        folds[start] = i
    return folds


# ---------- slim scrollbar ----------

class SlimScrollbar(tk.Canvas):
    """VS Code-like thin scrollbar: no arrows, rounded thumb."""

    def __init__(self, parent, orient: str = "vertical", command=None, theme_key: str = "dark"):
        t = THEMES[theme_key]
        super().__init__(
            parent,
            width=10 if orient == "vertical" else 10,
            height=10 if orient == "horizontal" else 0,
            highlightthickness=0,
            bd=0,
            bg=t["editor"],
            cursor="arrow",
        )
        self.orient = orient
        self.command = command
        self.theme_key = theme_key
        self.t = t
        self._start = 0.0
        self._end = 1.0
        self._scrollable = False
        self._drag_origin = None
        self._drag_start = 0.0
        self._drag_end = 1.0
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag_origin", None))

    def set_command(self, command) -> None:
        self.command = command

    def apply_theme(self, theme_key: str) -> None:
        self.theme_key = theme_key
        self.t = THEMES[theme_key]
        self.configure(bg=self.t["editor"])
        self._redraw()

    def set(self, first, last) -> None:
        try:
            self._start = max(0.0, min(1.0, float(first)))
            self._end = max(self._start, min(1.0, float(last)))
        except (TypeError, ValueError):
            self._start, self._end = 0.0, 1.0
        self._scrollable = self._start > 0.002 or self._end < 0.998
        self._redraw()

    def _thumb_range(self):
        if self.orient == "vertical":
            size = self.winfo_height() or 1
        else:
            size = self.winfo_width() or 1
        span = max(0.02, self._end - self._start)
        thumb = max(28, int(size * span))
        if thumb > size:
            thumb = size
        pos = int((size - thumb) * self._start)
        return pos, pos + thumb, size

    def _redraw(self) -> None:
        self.delete("all")
        t = self.t
        self.configure(bg=t["editor"])
        # hide entirely when content fits — no permanent gray bars
        if not self._scrollable:
            return
        pos0, pos1, size = self._thumb_range()
        if self.orient == "vertical":
            w = self.winfo_width() or 10
            self.create_rectangle(4, pos0 + 2, w - 4, max(pos0 + 3, pos1 - 2), fill=t["sb_thumb"], outline="", width=0)
        else:
            h = self.winfo_height() or 8
            self.create_rectangle(pos0 + 2, 3, max(pos0 + 3, pos1 - 2), h - 3, fill=t["sb_thumb"], outline="", width=0)

    def _on_press(self, event) -> None:
        pos0, pos1, size = self._thumb_range()
        coord = event.y if self.orient == "vertical" else event.x
        if coord < pos0 or coord > pos1:
            # jump page
            if self.command:
                if coord < pos0:
                    self.command("scroll", -1, "pages")
                else:
                    self.command("scroll", 1, "pages")
        self._drag_origin = coord
        self._drag_start, self._drag_end = self._start, self._end

    def _on_drag(self, event) -> None:
        if self._drag_origin is None or not self.command:
            return
        size = self.winfo_height() if self.orient == "vertical" else self.winfo_width() or 1
        span = max(0.02, self._drag_end - self._drag_start)
        thumb = max(28, int(size * span))
        usable = max(1, size - thumb)
        coord = event.y if self.orient == "vertical" else event.x
        delta = (coord - self._drag_origin) / usable
        first = max(0.0, min(1.0 - span, self._drag_start + delta))
        self.command("moveto", first)


# ---------- code editor with guides + fold ----------

class CodeEditor(tk.Frame):
    """Line numbers + syntax tags + indent guides + optional JSON fold."""

    def __init__(
        self,
        parent,
        theme_key: str = "dark",
        indent_size: int = 2,
        readonly: bool = False,
        foldable: bool = False,
    ):
        super().__init__(parent)
        ensure_fonts()
        self.theme_key = theme_key
        self.t = THEMES[theme_key]
        self.indent_size = max(1, indent_size)
        self.readonly = readonly
        self.foldable = foldable
        self.folds: dict[int, int] = {}  # open line -> close line
        self.folded: set[int] = set()  # collapsed open lines
        self._line_meta: dict[int, dict] = {}  # gutter hit-test
        self._build()
        self.apply_theme(theme_key)

    def _build(self) -> None:
        self.configure(bg=self.t["editor"], highlightthickness=0)

        gutter_w = 56 if self.foldable else 44
        self.gutter = tk.Canvas(self, width=gutter_w, highlightthickness=0, bd=0, bg=self.t["editor"])
        self.gutter.pack(side="left", fill="y")
        if self.foldable:
            self.gutter.configure(cursor="hand2")
            self.gutter.bind("<Button-1>", self._on_gutter_click)

        mid = tk.Frame(self, bg=self.t["editor"])
        mid.pack(side="left", fill="both", expand=True)

        self.vsb = SlimScrollbar(mid, orient="vertical", command=None, theme_key=self.theme_key)
        self.vsb.pack(side="right", fill="y")

        self.hsb = SlimScrollbar(mid, orient="horizontal", command=None, theme_key=self.theme_key)
        self.hsb.pack(side="bottom", fill="x")
        self.hsb.set_command(lambda *a: None)

        self.text = tk.Text(
            mid,
            wrap="none",
            undo=True,
            font=MONO_STACK,
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            insertwidth=2,
            exportselection=False,
        )
        self.text.pack(side="left", fill="both", expand=True)
        self.vsb.set_command(self.text.yview)
        self.hsb.set_command(self.text.xview)
        self.text.configure(yscrollcommand=self._on_scroll, xscrollcommand=self.hsb.set)

        if self.readonly:
            self.text.configure(state="disabled", cursor="arrow")

        self.text.bind("<KeyRelease>", self._on_edit)
        self.text.bind("<ButtonRelease-1>", self._refresh)
        self.text.bind("<MouseWheel>", self._on_mousewheel)
        self.text.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.gutter.bind("<MouseWheel>", self._on_mousewheel)
        self.vsb.bind("<MouseWheel>", self._on_mousewheel)
        self.hsb.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.text.bind("<<Paste>>", self._on_paste_async)
        self.text.bind("<<Cut>>", self._on_paste_async)
        self.bind("<Configure>", self._refresh)
        if self.foldable:
            self.text.bind("<Double-Button-1>", self._on_text_double_click)

        # tags
        self.text.tag_configure("key", foreground=self.t["key"])
        self.text.tag_configure("str", foreground=self.t["string"])
        self.text.tag_configure("num", foreground=self.t["number"])
        self.text.tag_configure("bool", foreground=self.t["bool"])
        self.text.tag_configure("null", foreground=self.t["null"])
        self.text.tag_configure("punct", foreground=self.t["punct"])
        self.text.tag_configure("guide", background=self.t["guide"])
        self.text.tag_configure("errorline", background=self.t["panel"])
        self.text.tag_configure("fold_hide", elide=True)
        self.text.tag_configure("folded_line", foreground=self.t["muted"])

    def apply_theme(self, theme_key: str) -> None:
        self.theme_key = theme_key
        self.t = THEMES[theme_key]
        t = self.t
        self.configure(bg=t["editor"])
        self.gutter.configure(bg=t["editor"])
        self.text.configure(
            bg=t["editor"],
            fg=t["ink"],
            insertbackground=t["ink"],
            selectbackground=t["selection"],
            selectforeground=t["ink"],
        )
        self.text.tag_configure("key", foreground=t["key"])
        self.text.tag_configure("str", foreground=t["string"])
        self.text.tag_configure("num", foreground=t["number"])
        self.text.tag_configure("bool", foreground=t["bool"])
        self.text.tag_configure("null", foreground=t["null"])
        self.text.tag_configure("punct", foreground=t["punct"])
        self.text.tag_configure("guide", background=t["guide"])
        self.text.tag_configure("fold_hide", elide=True)
        self.text.tag_configure("folded_line", foreground=t["muted"])
        if hasattr(self, "vsb") and isinstance(self.vsb, SlimScrollbar):
            self.vsb.apply_theme(theme_key)
        if hasattr(self, "hsb") and isinstance(self.hsb, SlimScrollbar):
            self.hsb.apply_theme(theme_key)
        self._refresh()

    def set_indent_size(self, n: int) -> None:
        self.indent_size = max(1, int(n))
        self._refresh()

    def _on_edit(self, _event=None) -> None:
        # editing invalidates fold map — keep highlighting live, drop stale folds
        if self.foldable and self.folds:
            self.folds.clear()
            self.folded.clear()
            self.text.tag_remove("fold_hide", "1.0", "end")
        self._refresh()

    def _on_scroll(self, *args) -> None:
        self.vsb.set(*args)
        self.after_idle(self._draw_gutter_and_guides)

    def _on_mousewheel(self, event: object) -> None:
        delta = getattr(event, "delta", 0)
        step = int(-1 * (delta / 120)) if delta else 0
        if step == 0:
            step = -1 if getattr(event, "num", 5) == 4 else 1
        self.text.yview_scroll(step, "units")
        self.after_idle(self._draw_gutter_and_guides)

    def _on_shift_mousewheel(self, event: object) -> None:
        delta = getattr(event, "delta", 0)
        step = int(-1 * (delta / 120)) if delta else 0
        self.text.xview_scroll(step, "units")

    def _on_paste_async(self, _event: object) -> str:
        self.after(10, self._refresh)
        return None  # type: ignore[return-value]

    def _refresh(self, _event: object = None) -> None:
        self._draw_gutter_and_guides()

    def set_text(self, raw: str, highlight: bool = True, is_json: bool = False) -> None:
        if self.readonly:
            self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.folds.clear()
        self.folded.clear()
        self.text.tag_remove("fold_hide", "1.0", "end")
        if raw:
            self.text.insert("1.0", raw)
        if self.readonly:
            self.text.configure(state="disabled")
        if highlight:
            if is_json:
                self._apply_json_highlight()
            self._apply_indent_guides()
            if self.foldable and is_json:
                self.folds = analyze_json_folds(raw)
        self._draw_gutter_and_guides()

    def get_text(self, visible_only: bool = False) -> str:
        if not visible_only or not self.folded:
            return self.text.get("1.0", "end-1c")
        # return content with folded bodies elided — still full source for copy/edit
        return self.text.get("1.0", "end-1c")

    def clear(self) -> None:
        self.set_text("", highlight=False)

    # ----- fold -----
    def expand_all(self) -> None:
        if not self.foldable:
            return
        self.folded.clear()
        self.text.tag_remove("fold_hide", "1.0", "end")
        self.text.tag_remove("folded_line", "1.0", "end")
        self._draw_gutter_and_guides()

    def collapse_all(self) -> None:
        if not self.foldable or not self.folds:
            return
        self.folded = set(self.folds.keys())
        self._apply_fold_tags()
        self._draw_gutter_and_guides()

    def _apply_fold_tags(self) -> None:
        self.text.tag_remove("fold_hide", "1.0", "end")
        self.text.tag_remove("folded_line", "1.0", "end")
        for start, end in self.folds.items():
            if start not in self.folded:
                continue
            # hide body between open and close lines
            self.text.tag_add("fold_hide", f"{start + 1}.0", f"{end}.0")
            self.text.tag_add("folded_line", f"{start}.0", f"{start}.end")

    def toggle_fold(self, line: int) -> None:
        if not self.foldable or line not in self.folds:
            return
        if line in self.folded:
            self.folded.discard(line)
        else:
            self.folded.add(line)
        self._apply_fold_tags()
        self._draw_gutter_and_guides()

    def _on_gutter_click(self, event) -> None:
        if not self.foldable:
            return
        y = event.y
        for line, meta in self._line_meta.items():
            if meta.get("y0", -1) <= y <= meta.get("y1", -1):
                if line in self.folds:
                    self.toggle_fold(line)
                return

    def _on_text_double_click(self, event) -> None:
        if not self.foldable:
            return
        try:
            index = self.text.index(f"@{event.x},{event.y}")
            line = int(index.split(".")[0])
        except tk.TclError:
            return
        if line in self.folds:
            self.toggle_fold(line)
            return "break"
        return None

    def _apply_json_highlight(self) -> None:
        text = self.get_text()
        for tag in ("key", "str", "num", "bool", "null", "punct"):
            self.text.tag_remove(tag, "1.0", "end")

        # "key": or "string"
        for m in re.finditer(r'"(?:\\.|[^"\\])*"', text):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            # key if followed by optional space and colon
            after = text[m.end() : m.end() + 4]
            if re.match(r"\s*:", after):
                self.text.tag_add("key", start, end)
            else:
                self.text.tag_add("str", start, end)

        for m in re.finditer(r"(?<![\w\".])-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", text):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            # skip if inside a string tag
            if "str" in self.text.tag_names(start) or "key" in self.text.tag_names(start):
                continue
            self.text.tag_add("num", start, end)

        for word, tag in (("true", "bool"), ("false", "bool"), ("null", "null")):
            for m in re.finditer(rf"(?<![\w\"])\b{word}\b(?![\w\"])", text):
                start = f"1.0+{m.start()}c"
                if "str" in self.text.tag_names(start) or "key" in self.text.tag_names(start):
                    continue
                self.text.tag_add(tag, start, f"1.0+{m.end()}c")

        for m in re.finditer(r"[{}\[\],:]", text):
            start = f"1.0+{m.start()}c"
            if "str" in self.text.tag_names(start) or "key" in self.text.tag_names(start):
                continue
            self.text.tag_add("punct", start, f"1.0+{m.end()}c")

    def _apply_indent_guides(self) -> None:
        """Color space columns at each indent level → vertical guide lines."""
        self.text.tag_remove("guide", "1.0", "end")
        raw = self.get_text()
        if not raw:
            return
        step = self.indent_size
        for i, line in enumerate(raw.split("\n"), start=1):
            if not line or line[0] not in " \t":
                continue
            # expand tabs conceptually as indent_size spaces
            expanded = line.replace("\t", " " * step)
            lead = len(expanded) - len(expanded.lstrip(" "))
            # original line length for indexing (guides only on spaces)
            for level in range(1, lead // step + 1):
                col = (level - 1) * step
                if col >= len(line):
                    break
                # only mark if that column is still a space in original
                if line[col] != " ":
                    # tab-occupied: skip
                    continue
                # draw a 1-char wide guide at the start of each indent unit
                self.text.tag_add("guide", f"{i}.{col}", f"{i}.{col + 1}")
                # optional: also mark middle for stronger line when step>=2
                if step >= 2 and col + 1 < len(line) and line[col + 1] == " ":
                    # keep single-column line — cleaner VS Code look
                    pass

    def _draw_gutter_and_guides(self) -> None:
        self.gutter.delete("all")
        self._line_meta.clear()
        t = self.t
        try:
            first = self.text.index("@0,0")
            last = self.text.index(f"@0,{self.text.winfo_height()}")
        except tk.TclError:
            return
        start_line = int(first.split(".")[0])
        end_line = int(last.split(".")[0])
        total = int(self.text.index("end-1c").split(".")[0]) or 1

        gutter_w = 56 if self.foldable else 44
        num_x = 44 if self.foldable else 36
        for lineno in range(start_line, min(end_line + 3, total + 1)):
            try:
                dline = self.text.dlineinfo(f"{lineno}.0")
            except tk.TclError:
                continue
            if not dline:
                continue
            y = dline[1]
            line_h = dline[3]
            cy = y + line_h / 2
            self._line_meta[lineno] = {"y0": y, "y1": y + line_h}
            self.gutter.create_text(
                num_x,
                cy,
                text=str(lineno),
                anchor="e",
                font=(_fonts()[0], 9),
                fill=t["lineno"],
            )
            if self.foldable and lineno in self.folds:
                collapsed = lineno in self.folded
                mark = "＋" if collapsed else "－"
                # subtle hit target
                self.gutter.create_rectangle(
                    2,
                    y + 2,
                    16,
                    y + line_h - 2,
                    fill=t["panel"],
                    outline=t["border"],
                    width=1,
                )
                self.gutter.create_text(
                    9,
                    cy,
                    text=mark,
                    anchor="center",
                    font=(_fonts()[0], 9, "bold"),
                    fill=t["accent"],
                )
        self.gutter.configure(bg=t["editor"], width=gutter_w)


# ---------- app ----------

class ToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        ensure_fonts()
        self.theme_name = "dark"
        self.t = THEMES[self.theme_name]
        self.title(f"{APP_TITLE}  ·  {APP_SUB}  v{APP_VERSION}")
        self.geometry("1280x860")
        self.minsize(1000, 680)
        self._center(1280, 860)
        self._apply_root_theme()
        self._build()
        self.after(250, self._tick_now)

    def _center(self, w: int, h: int) -> None:
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}")

    def _apply_root_theme(self) -> None:
        t = self.t
        self.configure(bg=t["chrome"])
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=t["chrome"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=t["panel"],
            foreground=t["muted"],
            padding=(20, 12),
            font=UI_STACK,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", t["chrome"])],
            foreground=[("selected", t["accent"])],
        )
        style.configure("Treeview", background=t["editor"], fieldbackground=t["editor"], foreground=t["ink"], borderwidth=0)
        style.configure("Treeview.Heading", background=t["panel2"], foreground=t["muted"], font=UI_SM)
        style.map("Treeview", background=[("selected", t["tree_sel"])], foreground=[("selected", t["ink"])])
        style.configure("TCombobox", fieldbackground=t["field"], background=t["panel"], foreground=t["ink"], bordercolor=t["border"])
        style.configure(
            "Dark.TCombobox",
            fieldbackground=t["field"],
            background=t["panel"],
            foreground=t["ink"],
            bordercolor=t["border"],
            lightcolor=t["border"],
            darkcolor=t["border"],
            arrowcolor=t["muted"],
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", t["field"])],
            foreground=[("readonly", t["ink"])],
            background=[("readonly", t["panel"])],
            selectbackground=[("readonly", t["field"])],
            selectforeground=[("readonly", t["ink"])],
        )
        style.configure("Vertical.TScrollbar", troughcolor=t["chrome"], background=t["border"], bordercolor=t["chrome"])

    # ----- chrome -----
    def _build(self) -> None:
        t = self.t

        top = tk.Frame(self, bg=t["chrome"], height=52)
        top.pack(fill="x", padx=16, pady=(14, 4))
        top.pack_propagate(False)

        mark = tk.Frame(top, bg=t["accent"], width=4, height=28)
        mark.pack(side="left", padx=(0, 12), pady=10)
        mark.pack_propagate(False)

        title_box = tk.Frame(top, bg=t["chrome"])
        title_box.pack(side="left", fill="y", pady=6)
        tk.Label(title_box, text=APP_TITLE, bg=t["chrome"], fg=t["ink"], font=UI_TITLE).pack(anchor="w")
        tk.Label(title_box, text="离线本地 · 不联网 · 开发者工具", bg=t["chrome"], fg=t["muted"], font=UI_SM).pack(anchor="w")

        right = tk.Frame(top, bg=t["chrome"])
        right.pack(side="right", pady=8)
        self.theme_btn = self._chip(right, f"主题：{t['name']}", self._toggle_theme)
        self.theme_btn.pack(side="left", padx=(0, 8))
        self._chip(right, "复制输出", self._copy_output).pack(side="left", padx=(0, 4))

        status_bar = tk.Frame(self, bg=t["chrome"])
        status_bar.pack(fill="x", padx=18, pady=(0, 6))
        self.status_var = tk.StringVar(value="就绪 · 可直接粘贴 JSON 或时间戳")
        tk.Label(status_bar, textvariable=self.status_var, bg=t["chrome"], fg=t["muted"], font=UI_SM, anchor="w").pack(side="left")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.notebook = notebook

        self.tab_json = tk.Frame(notebook, bg=t["chrome"])
        self.tab_time = tk.Frame(notebook, bg=t["chrome"])
        notebook.add(self.tab_json, text="  JSON  ")
        notebook.add(self.tab_time, text="  时间戳  ")

        self._build_json_tab(self.tab_json)
        self._build_time_tab(self.tab_time)

    def _chip(self, parent, text, command, accent=False):
        t = self.t
        if accent:
            bg, fg, ah = t["accent"], "#FFFFFF", t["accent_hover"]
        else:
            bg, fg, ah = t["panel"], t["ink"], t["border"]
        btn = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=UI_SM,
            padx=12,
            pady=6,
            cursor="hand2",
            takefocus=True,
        )
        btn.bind("<Enter>", lambda e, b=btn, c=ah: b.configure(bg=c))
        btn.bind("<Leave>", lambda e, b=btn, c=bg: b.configure(bg=c))
        btn.bind("<Button-1>", lambda e, c=command: c())
        return btn

    def _btn(self, parent, text, command, primary=False):
        t = self.t
        if primary:
            bg, fg, ah = t["accent"], "#FFFFFF", t["accent_hover"]
        else:
            bg, fg, ah = t["panel"], t["ink"], t["border"]
        btn = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=UI_BTN,
            padx=14,
            pady=7,
            cursor="hand2",
        )
        btn.bind("<Enter>", lambda e, b=btn, c=ah: b.configure(bg=c))
        btn.bind("<Leave>", lambda e, b=btn, c=bg: b.configure(bg=c))
        btn.bind("<Button-1>", lambda e, c=command: c())
        return btn

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _copy_text(self, value: str, label: str = "结果") -> None:
        self.clipboard_clear()
        self.clipboard_append(value or "")
        self._set_status(f"已复制{label}")

    def _copy_output(self) -> None:
        if hasattr(self, "out_editor"):
            self._copy_text(self.out_editor.get_text(), "输出")

    def _toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.t = THEMES[self.theme_name]
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        # full rebuild keeps theme consistent
        for child in self.winfo_children():
            child.destroy()
        self._apply_root_theme()
        self._build()
        self._set_status(f"已切换到{self.t['name']}主题")

    # ----- JSON tab -----
    def _build_json_tab(self, parent: tk.Widget) -> None:
        t = self.t

        toolbar = tk.Frame(parent, bg=t["chrome"])
        toolbar.pack(fill="x", padx=4, pady=(4, 8))

        self._btn(toolbar, "格式化", self._json_format, primary=True).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "重新缩进输出", self._json_reindent_output).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "全部展开", self._json_expand_all).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "全部折叠", self._json_collapse_all).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "压缩", self._json_minify).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "校验", self._json_validate).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "交换 ⇄", self._json_swap).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "清空", self._json_clear).pack(side="left", padx=(0, 12))

        tk.Label(toolbar, text="缩进", bg=t["chrome"], fg=t["muted"], font=UI_SM).pack(side="left", padx=(0, 6))
        self.indent_var = tk.StringVar(value="2")
        self.indent_btns: dict[str, tk.Label] = {}
        for label, val in (("2", "2"), ("4", "4"), ("8", "8"), ("Tab", "tab")):
            b = self._indent_chip(toolbar, label, val)
            b.pack(side="left", padx=(0, 4))
            self.indent_btns[val] = b
        self._sync_indent_chips()

        tk.Frame(toolbar, bg=t["chrome"], width=8).pack(side="left")
        self.guides_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            toolbar,
            text="缩进参考线",
            variable=self.guides_var,
            command=self._on_guides_toggle,
            bg=t["chrome"],
            fg=t["muted"],
            activebackground=t["chrome"],
            activeforeground=t["accent"],
            selectcolor=t["panel"],
            font=UI_SM,
        ).pack(side="left", padx=(0, 10))

        self.tree_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            toolbar,
            text="结构树",
            variable=self.tree_var,
            command=self._on_tree_toggle,
            bg=t["chrome"],
            fg=t["muted"],
            activebackground=t["chrome"],
            activeforeground=t["accent"],
            selectcolor=t["panel"],
            font=UI_SM,
        ).pack(side="left")

        # ---- left / right layout ----
        self.json_split = tk.PanedWindow(
            parent,
            orient="horizontal",
            bg=t["border"],
            sashwidth=6,
            sashrelief="flat",
            opaqueresize=True,
        )
        self.json_split.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # left: input
        in_panel = tk.Frame(self.json_split, bg=t["panel"])
        in_header = tk.Frame(in_panel, bg=t["panel"])
        in_header.pack(fill="x")
        tk.Label(in_header, text="输入 · 粘贴原始 JSON", bg=t["panel"], fg=t["muted"], font=UI_SM).pack(
            side="left", padx=10, pady=6
        )
        self.in_editor = CodeEditor(in_panel, theme_key=self.theme_name, indent_size=2, foldable=False)
        self.in_editor.pack(fill="both", expand=True)

        # right workspace: foldable output (+ optional tree)
        workspace = tk.Frame(self.json_split, bg=t["chrome"])
        self.work_split = tk.PanedWindow(
            workspace,
            orient="horizontal",
            bg=t["border"],
            sashwidth=4,
            sashrelief="flat",
            opaqueresize=True,
        )
        self.work_split.pack(fill="both", expand=True)

        out_panel = tk.Frame(self.work_split, bg=t["panel"])
        out_header = tk.Frame(out_panel, bg=t["panel"])
        out_header.pack(fill="x")
        tk.Label(out_header, text="输出 · 点击左侧 ＋/－ 或双击括号折叠", bg=t["panel"], fg=t["ink"], font=UI_SM).pack(
            side="left", padx=10, pady=6
        )
        tk.Label(out_header, text="Ctrl+S 复制输出", bg=t["panel"], fg=t["dim"], font=UI_SM).pack(side="right", padx=10, pady=6)
        self.out_editor = CodeEditor(out_panel, theme_key=self.theme_name, readonly=False, foldable=True)
        self.out_editor.pack(fill="both", expand=True)
        self.out_editor.text.bind("<Control-s>", self._on_copy_output_key)
        self.out_editor.text.bind("<Control-S>", self._on_copy_output_key)

        self.tree_host = tk.Frame(self.work_split, bg=t["chrome"], width=220)
        tree_header = tk.Frame(self.tree_host, bg=t["panel"])
        tree_header.pack(fill="x")
        tk.Label(tree_header, text="结构树", bg=t["panel"], fg=t["muted"], font=UI_SM).pack(side="left", padx=10, pady=6)
        self.tree_wrap = tk.Frame(self.tree_host, bg=t["panel"])
        self.tree_wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(self.tree_wrap, columns=("preview",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="键 / 索引")
        self.tree.heading("preview", text="值")
        self.tree.column("#0", width=100, stretch=True)
        self.tree.column("preview", width=110, stretch=True)
        tree_sb = SlimScrollbar(self.tree_wrap, orient="vertical", command=self.tree.yview, theme_key=self.theme_name)
        self.tree.configure(yscrollcommand=tree_sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_sb.pack(side="right", fill="y")

        self.out_panel = out_panel
        self.work_split.add(out_panel, minsize=420)

        self.json_split.add(in_panel, minsize=260)
        self.json_split.add(workspace, minsize=420)

        sample = {
            "name": "JSON Lab",
            "version": APP_VERSION,
            "features": ["格式化", "语法高亮", "缩进参考线", "折叠展开"],
            "meta": {
                "offline": True,
                "created_at": 1726732200,
                "ratio": 0.98,
                "note": "中文与 unicode 测试 ✓",
            },
        }
        self.in_editor.set_text(json.dumps(sample, ensure_ascii=False, indent=2), highlight=True, is_json=True)
        self._json_format(silent=True)
        self._show_tree(self.tree_var.get())
        self.after(80, self._apply_default_sash)

    def _apply_default_sash(self) -> None:
        """Output side gets more width (~62%)."""
        try:
            total = self.json_split.winfo_width()
            if total < 400:
                self.after(120, self._apply_default_sash)
                return
            left = max(260, int(total * 0.36))
            self.json_split.sash_place(0, left, 0)
            if self.tree_var.get():
                w = self.work_split.winfo_width()
                self.work_split.sash_place(0, max(320, w - 220), 0)
        except tk.TclError:
            pass

    def _json_expand_all(self) -> None:
        self.out_editor.expand_all()
        self._set_status("已全部展开")

    def _json_collapse_all(self) -> None:
        self.out_editor.collapse_all()
        self._set_status("已全部折叠（点击 ＋ 展开）")

    def _on_copy_output_key(self, _event=None):
        self._copy_output()
        return "break"

    def _json_reindent_output(self) -> None:
        raw = self.out_editor.get_text()
        if not raw.strip():
            self._set_status("输出为空")
            return
        try:
            pretty = format_json_text(raw, self._indent_value())
            self.out_editor.set_text(pretty, highlight=True, is_json=True)
            if not self.guides_var.get():
                self.out_editor.text.tag_remove("guide", "1.0", "end")
            self._refresh_tree_from_text(pretty)
            self.out_editor.text.focus_set()
            self._set_status(f"输出已重新缩进 · {len(self.out_editor.folds)} 处可折叠")
        except json.JSONDecodeError as e:
            self._set_status(f"输出不是合法 JSON：{e}")
            messagebox.showerror("JSON 错误", f"输出区内容无法解析：\n{e}")

    def _indent_chip(self, parent, label: str, value: str) -> tk.Label:
        t = self.t
        selected = self.indent_var.get() == value
        bg = t["accent"] if selected else t["panel"]
        fg = "#FFFFFF" if selected else t["muted"]
        btn = tk.Label(parent, text=label, bg=bg, fg=fg, font=UI_SM, padx=10, pady=5, cursor="hand2")

        def on_click(_e=None, v=value):
            self.indent_var.set(v)
            self._sync_indent_chips()
            self._on_indent_change()

        def on_enter(_e=None, v=value):
            if self.indent_var.get() != v:
                btn.configure(bg=t["border"])

        def on_leave(_e=None, v=value):
            self._sync_indent_chips()

        btn.bind("<Button-1>", on_click)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _sync_indent_chips(self) -> None:
        if not hasattr(self, "indent_btns"):
            return
        t = self.t
        cur = self.indent_var.get()
        for val, btn in self.indent_btns.items():
            selected = val == cur
            btn.configure(
                bg=t["accent"] if selected else t["panel"],
                fg="#FFFFFF" if selected else t["muted"],
            )

    def _indent_value(self) -> int | str:
        raw = self.indent_var.get() if hasattr(self, "indent_var") else "2"
        return "    " if raw == "tab" else int(raw)

    def _on_indent_change(self, _e=None) -> None:
        ind = self._indent_value()
        size = 4 if ind == "    " else int(ind)
        self.in_editor.set_indent_size(size)
        self.out_editor.set_indent_size(size)
        # re-pretty current output in place (user's working buffer)
        if self.out_editor.get_text().strip():
            self._json_reindent_output()

    def _on_guides_toggle(self) -> None:
        if self.guides_var.get():
            self.out_editor._apply_indent_guides()
            self.in_editor._apply_indent_guides()
            self._set_status("已开启缩进参考线")
        else:
            self.out_editor.text.tag_remove("guide", "1.0", "end")
            self.in_editor.text.tag_remove("guide", "1.0", "end")
            self._set_status("已关闭缩进参考线")

    def _on_tree_toggle(self) -> None:
        self._show_tree(self.tree_var.get())

    def _show_tree(self, visible: bool) -> None:
        name = str(self.tree_host)
        try:
            panes = [str(p) for p in self.work_split.panes()]
            if visible:
                if name not in panes:
                    self.work_split.add(self.tree_host, minsize=180)
                w = self.work_split.winfo_width() or 900
                self.work_split.sash_place(0, max(300, w - 240), 0)
            else:
                if name in panes:
                    self.work_split.forget(name)
        except tk.TclError:
            pass

    def _json_clear(self) -> None:
        self.in_editor.clear()
        self.out_editor.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._set_status("已清空")

    def _json_swap(self) -> None:
        a = self.in_editor.get_text()
        b = self.out_editor.get_text()
        self.in_editor.set_text(b, highlight=True)
        self.out_editor.set_text(a, highlight=True, is_json=self._looks_json(b))
        self._refresh_tree_from_text(self.out_editor.get_text() if self._looks_json(b) else "")
        self._set_status("已交换输入 / 输出")

    @staticmethod
    def _looks_json(text: str) -> bool:
        try:
            json.loads(text)
            return True
        except Exception:
            return False

    def _refresh_tree_from_text(self, raw: str) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not raw.strip():
            return
        try:
            data = json.loads(raw)
        except Exception:
            return

        def walk(parent, key, value):
            label = key if key is not None else "root"
            if isinstance(value, dict):
                node = self.tree.insert(parent, "end", text=str(label), values=(json_preview(value),), open=True)
                for k, v in value.items():
                    walk(node, str(k), v)
            elif isinstance(value, list):
                node = self.tree.insert(parent, "end", text=str(label), values=(json_preview(value),), open=True)
                for i, v in enumerate(value):
                    walk(node, f"[{i}]", v)
            else:
                self.tree.insert(parent, "end", text=str(label), values=(json_preview(value),))

        walk("", None, data)
        # expand first levels
        for item in self.tree.get_children():
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                self.tree.item(child, open=True)

    def _json_format(self, silent: bool = False) -> None:
        raw = self.in_editor.get_text()
        if not raw.strip():
            self._set_status("输入为空 · 请粘贴 JSON")
            return
        try:
            pretty = format_json_text(raw, self._indent_value())
            self.out_editor.set_text(pretty, highlight=True, is_json=True)
            if not self.guides_var.get():
                self.out_editor.text.tag_remove("guide", "1.0", "end")
            # refresh input highlight in place
            self.in_editor._apply_json_highlight()
            if self.guides_var.get():
                self.in_editor._apply_indent_guides()
            else:
                self.in_editor.text.tag_remove("guide", "1.0", "end")
            self._refresh_tree_from_text(pretty)
            self.out_editor.text.focus_set()
            nfold = len(self.out_editor.folds)
            self._set_status(f"格式化成功 · {len(pretty.splitlines())} 行 · {nfold} 处可折叠 · 可直接编辑输出")
        except json.JSONDecodeError as e:
            self._set_status(f"JSON 解析失败：{e}")
            if not silent:
                messagebox.showerror("JSON 错误", f"解析失败：\n{e}")

    def _json_minify(self) -> None:
        raw = self.in_editor.get_text()
        if not raw.strip():
            self._set_status("输入为空")
            return
        try:
            compact = minify_json_text(raw)
            self.out_editor.set_text(compact, highlight=True, is_json=True)
            self._refresh_tree_from_text(raw)
            self._set_status(f"压缩成功 · {len(compact)} 字符")
        except json.JSONDecodeError as e:
            self._set_status(f"JSON 解析失败：{e}")
            messagebox.showerror("JSON 错误", f"解析失败：\n{e}")

    def _json_validate(self) -> None:
        raw = self.in_editor.get_text()
        if not raw.strip():
            self._set_status("输入为空")
            return
        try:
            data = json.loads(raw)
            kind = type(data).__name__
            if isinstance(data, dict):
                extra = f"，{len(data)} 个键"
            elif isinstance(data, list):
                extra = f"，{len(data)} 个元素"
            else:
                extra = ""
            self._set_status(f"JSON 合法（{kind}{extra}）")
            messagebox.showinfo("校验通过", f"JSON 合法。\n类型: {kind}{extra}")
        except json.JSONDecodeError as e:
            self._set_status(f"JSON 不合法：{e}")
            messagebox.showerror("JSON 错误", f"JSON 不合法：\n{e}")

    # ----- timestamp tab -----
    def _build_time_tab(self, parent: tk.Widget) -> None:
        t = self.t
        outer = tk.Frame(parent, bg=t["chrome"])
        outer.pack(fill="both", expand=True, padx=8, pady=8)

        # now card
        now_card = tk.Frame(outer, bg=t["panel"], highlightbackground=t["border"], highlightthickness=1)
        now_card.pack(fill="x", pady=(0, 10))
        tk.Label(now_card, text="当前时间戳", bg=t["panel"], fg=t["muted"], font=UI_SM).pack(anchor="w", padx=16, pady=(12, 2))

        self.now_human_var = tk.StringVar(value="—")
        self.now_sec_var = tk.StringVar(value="—")
        self.now_ms_var = tk.StringVar(value="—")

        grid = tk.Frame(now_card, bg=t["panel"])
        grid.pack(fill="x", padx=16, pady=(4, 12))
        self._metric(grid, 0, "本地时间", self.now_human_var, small=True)
        self._metric(grid, 1, "秒时间戳", self.now_sec_var)
        self._metric(grid, 2, "毫秒时间戳", self.now_ms_var)

        btn_row = tk.Frame(now_card, bg=t["panel"])
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        self._btn(btn_row, "复制秒", lambda: self._copy_text(self.now_sec_var.get(), "秒时间戳")).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "复制毫秒", lambda: self._copy_text(self.now_ms_var.get(), "毫秒时间戳")).pack(side="left")

        # converters
        row = tk.Frame(outer, bg=t["chrome"])
        row.pack(fill="both", expand=True)
        row.grid_columnconfigure(0, weight=1, uniform="c")
        row.grid_columnconfigure(1, weight=1, uniform="c")
        row.grid_rowconfigure(0, weight=1)

        # ts -> time
        left = tk.Frame(row, bg=t["panel"], highlightbackground=t["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(left, text="时间戳 → 时间", bg=t["panel"], fg=t["ink"], font=UI_TITLE).pack(anchor="w", padx=16, pady=(14, 10))

        form = tk.Frame(left, bg=t["panel"])
        form.pack(fill="x", padx=16)
        tk.Label(form, text="时间戳", bg=t["panel"], fg=t["muted"], font=UI_SM, width=10, anchor="w").grid(row=0, column=0, sticky="w")
        self.ts_in_var = tk.StringVar()
        self._entry(form, self.ts_in_var).grid(row=0, column=1, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        unit_row = tk.Frame(left, bg=t["panel"])
        unit_row.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(unit_row, text="单位", bg=t["panel"], fg=t["muted"], font=UI_SM, width=10, anchor="w").pack(side="left")
        self.ts_unit_var = tk.StringVar(value="auto")
        for label, val in (("自动", "auto"), ("秒", "s"), ("毫秒", "ms")):
            tk.Radiobutton(
                unit_row,
                text=label,
                variable=self.ts_unit_var,
                value=val,
                bg=t["panel"],
                fg=t["ink"],
                font=UI_SM,
                activebackground=t["panel"],
                activeforeground=t["accent"],
                selectcolor=t["field"],
            ).pack(side="left", padx=(0, 12))

        brow = tk.Frame(left, bg=t["panel"])
        brow.pack(fill="x", padx=16, pady=(14, 8))
        self._btn(brow, "转换", self._ts_to_time, primary=True).pack(side="left", padx=(0, 6))
        self._btn(brow, "填入当前秒", lambda: self.ts_in_var.set(self.now_sec_var.get())).pack(side="left")

        self.ts_local_var = tk.StringVar(value="—")
        self.ts_utc_var = tk.StringVar(value="—")
        self.ts_cst_var = tk.StringVar(value="—")
        self.ts_unit_out_var = tk.StringVar(value="—")
        box = tk.Frame(left, bg=t["panel"])
        box.pack(fill="x", padx=16, pady=(4, 16))
        self._kv(box, "识别单位", self.ts_unit_out_var)
        self._kv(box, "本地时间", self.ts_local_var)
        self._kv(box, "UTC", self.ts_utc_var)
        self._kv(box, "北京时间", self.ts_cst_var)
        self._btn(box, "复制本地时间", lambda: self._copy_text(self.ts_local_var.get(), "本地时间")).pack(anchor="w", pady=(8, 0))

        # time -> ts
        right = tk.Frame(row, bg=t["panel"], highlightbackground=t["border"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(right, text="时间 → 时间戳", bg=t["panel"], fg=t["ink"], font=UI_TITLE).pack(anchor="w", padx=16, pady=(14, 10))

        form2 = tk.Frame(right, bg=t["panel"])
        form2.pack(fill="x", padx=16)
        tk.Label(form2, text="日期时间", bg=t["panel"], fg=t["muted"], font=UI_SM, width=10, anchor="w").grid(row=0, column=0, sticky="w")
        self.time_in_var = tk.StringVar()
        self._entry(form2, self.time_in_var).grid(row=0, column=1, sticky="ew")
        form2.grid_columnconfigure(1, weight=1)
        tk.Label(form2, text="支持 2026-09-20 12:30:00 / ISO8601 / 20260920", bg=t["panel"], fg=t["dim"], font=UI_SM).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        tz_row = tk.Frame(right, bg=t["panel"])
        tz_row.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(tz_row, text="输入时区", bg=t["panel"], fg=t["muted"], font=UI_SM, width=10, anchor="w").pack(side="left")
        self.tz_in_var = tk.StringVar(value="local")
        for label, val in (("本机", "local"), ("UTC", "utc"), ("北京 +8", "cst")):
            tk.Radiobutton(
                tz_row,
                text=label,
                variable=self.tz_in_var,
                value=val,
                bg=t["panel"],
                fg=t["ink"],
                font=UI_SM,
                activebackground=t["panel"],
                activeforeground=t["accent"],
                selectcolor=t["field"],
            ).pack(side="left", padx=(0, 12))

        brow2 = tk.Frame(right, bg=t["panel"])
        brow2.pack(fill="x", padx=16, pady=(14, 8))
        self._btn(brow2, "转换", self._time_to_ts, primary=True).pack(side="left", padx=(0, 6))
        self._btn(brow2, "填入当前时间", self._fill_now_human).pack(side="left")

        self.out_sec_var = tk.StringVar(value="—")
        self.out_ms_var = tk.StringVar(value="—")
        self.out_us_var = tk.StringVar(value="—")
        self.out_utc_var = tk.StringVar(value="—")
        box2 = tk.Frame(right, bg=t["panel"])
        box2.pack(fill="x", padx=16, pady=(4, 16))
        self._kv(box2, "秒时间戳", self.out_sec_var)
        self._kv(box2, "毫秒时间戳", self.out_ms_var)
        self._kv(box2, "微秒时间戳", self.out_us_var)
        self._kv(box2, "UTC 显示", self.out_utc_var)
        crow = tk.Frame(box2, bg=t["panel"])
        crow.pack(anchor="w", pady=(8, 0))
        self._btn(crow, "复制秒", lambda: self._copy_text(self.out_sec_var.get(), "秒时间戳")).pack(side="left", padx=(0, 6))
        self._btn(crow, "复制毫秒", lambda: self._copy_text(self.out_ms_var.get(), "毫秒时间戳")).pack(side="left")

        hint = tk.Label(
            outer,
            text="时间戳自动识别：10 位 ≈ 秒 · 13 位 ≈ 毫秒 · 16 位 ≈ 微秒",
            bg=t["chrome"],
            fg=t["dim"],
            font=UI_SM,
        )
        hint.pack(anchor="w", pady=(8, 0))

        self._tick_now()
        self.ts_in_var.set(self.now_sec_var.get())
        self._ts_to_time()
        self._fill_now_human()
        self._time_to_ts()

    def _entry(self, parent, var):
        t = self.t
        e = tk.Entry(
            parent,
            textvariable=var,
            font=MONO_STACK,
            relief="flat",
            bg=t["input_bg"],
            fg=t["ink"],
            insertbackground=t["ink"],
            highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["accent"],
        )
        return e

    def _metric(self, parent, col, label, var, small=False):
        t = self.t
        cell = tk.Frame(parent, bg=t["panel2"], highlightbackground=t["border"], highlightthickness=1)
        cell.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 8), pady=4, ipady=8)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(cell, text=label, bg=t["panel2"], fg=t["muted"], font=UI_SM).pack(anchor="w", padx=12, pady=(8, 2))
        font = UI_STACK if small else UI_NUM
        tk.Label(cell, textvariable=var, bg=t["panel2"], fg=t["accent"] if not small else t["ink"], font=font, anchor="w").pack(
            anchor="w", padx=12, pady=(0, 10)
        )

    def _kv(self, parent, label, var):
        t = self.t
        row = tk.Frame(parent, bg=t["panel"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=t["panel"], fg=t["muted"], font=UI_SM, width=10, anchor="w").pack(side="left")
        tk.Label(row, textvariable=var, bg=t["panel"], fg=t["ink"], font=MONO_STACK, anchor="w").pack(side="left", fill="x", expand=True)

    def _tick_now(self) -> None:
        try:
            dt = now_dt()
            sec = int(dt.timestamp())
            ms = int(round(dt.timestamp() * 1000))
            self.now_human_var.set(dt.strftime("%Y-%m-%d %H:%M:%S %z"))
            self.now_sec_var.set(str(sec))
            self.now_ms_var.set(str(ms))
        except Exception:
            pass
        self.after(1000, self._tick_now)

    def _fill_now_human(self) -> None:
        self.time_in_var.set(now_dt().strftime("%Y-%m-%d %H:%M:%S"))
        self.tz_in_var.set("local")

    @staticmethod
    def _fmt_offset(dt: datetime) -> str:
        off = dt.strftime("%z")
        if not off:
            return ""
        return f"{off[:3]}:{off[3:]}"

    def _ts_to_time(self) -> None:
        raw = self.ts_in_var.get().strip().replace(",", "")
        if not raw:
            self._set_status("请输入时间戳")
            return
        try:
            value: float = int(raw) if re.fullmatch(r"-?\d+", raw) else float(raw)
            unit = self.ts_unit_var.get()
            if unit == "auto":
                unit = detect_ts_unit(value)
            dt = ts_to_dt(value, unit)
            ms3 = dt.microsecond // 1000
            self.ts_unit_out_var.set(unit)
            self.ts_local_var.set(f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{ms3:03d} {self._fmt_offset(dt)}")
            utc = dt.astimezone(timezone.utc)
            self.ts_utc_var.set(f"{utc.strftime('%Y-%m-%d %H:%M:%S')}.{ms3:03d} UTC")
            cst = dt.astimezone(CST)
            self.ts_cst_var.set(f"{cst.strftime('%Y-%m-%d %H:%M:%S')}.{ms3:03d} +08:00")
            self._set_status(f"转换成功 · 识别为 {unit}")
        except Exception as e:
            self._set_status(f"转换失败：{e}")
            messagebox.showerror("转换失败", str(e))

    def _time_to_ts(self) -> None:
        try:
            dt = parse_human_time(self.time_in_var.get())
            mode = self.tz_in_var.get()
            if mode == "utc":
                dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            elif mode == "cst":
                dt = dt.replace(tzinfo=CST) if dt.tzinfo is None else dt.astimezone(CST)
            elif dt.tzinfo is None:
                dt = dt.astimezone()
            self.out_sec_var.set(str(dt_to_ts(dt, "s")))
            self.out_ms_var.set(str(dt_to_ts(dt, "ms")))
            self.out_us_var.set(str(dt_to_ts(dt, "μs")))
            utc = dt.astimezone(timezone.utc)
            self.out_utc_var.set(f"{utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            self._set_status("时间 → 时间戳 成功")
        except Exception as e:
            self._set_status(f"转换失败：{e}")
            messagebox.showerror("转换失败", str(e))


def main() -> int:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = ToolApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
