import os
from tkinter import ttk
from typing import Callable

import customtkinter as ctk

from config import EXCLUDE_FOLDERS, EXCLUDE_FILES, EXCLUDE_EXTENSIONS

# ── Palette (keep in sync with ui.py) ─────────────────────────────────────────
BG     = '#111113'
SIDE   = '#1C1C1E'
CARD   = '#2C2C2E'
BORDER = '#3A3A3C'
TEXT   = '#F2F2F7'
MUTED  = '#8E8E93'
BLUE   = '#0A84FF'
SEL_BG = '#1E3A5F'

CHECKED   = '☑'
UNCHECKED = '☐'


def apply_treeview_style() -> None:
    """Dark style for ttk.Treeview that matches the CTk theme."""
    style = ttk.Style()
    style.theme_use('default')

    style.configure('Dark.Treeview',
        background=SIDE,
        foreground=MUTED,
        fieldbackground=SIDE,
        borderwidth=0,
        rowheight=26,
        font=('Segoe UI', 11),
    )
    style.configure('Dark.Treeview.Heading',
        background=SIDE,
        foreground=MUTED,
        borderwidth=0,
    )
    style.map('Dark.Treeview',
        background=[('selected', SEL_BG)],
        foreground=[('selected', TEXT)],
    )
    style.configure('Dark.Treeview',
        indent=16,
    )


class FileTree:
    """
    Wraps ttk.Treeview with checkbox logic and dark styling.
    Folders are collapsed by default; toggling propagates to children
    and bubbles up to parents.
    """

    def __init__(self, parent: ctk.CTkFrame, on_change: Callable):
        self.on_change = on_change
        self._checks: dict[str, bool] = {}   # iid -> bool
        self._paths:  dict[str, str]  = {}   # iid -> absolute path

        apply_treeview_style()

        self._tv = ttk.Treeview(parent, show='tree', style='Dark.Treeview',
                                selectmode='none')
        self._tv.pack(fill='both', expand=True, padx=4, pady=4)
        self._tv.bind('<Button-1>', self._on_click)

        # Scrollbar
        sb = ctk.CTkScrollbar(parent, command=self._tv.yview,
                              button_color=BORDER, button_hover_color=MUTED)
        sb.pack(side='right', fill='y')
        self._tv.configure(yscrollcommand=sb.set)

    # ── Loading ────────────────────────────────────────────────────────────────

    def load(self, base_path: str) -> None:
        self._tv.delete(*self._tv.get_children())
        self._checks.clear()
        self._paths.clear()
        self._load_recursive(base_path, '')

    def _load_recursive(self, path: str, parent_iid: str) -> None:
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return

        for name in entries:
            full = os.path.join(path, name)

            if name in EXCLUDE_FOLDERS:
                continue

            if os.path.isdir(full):
                iid = self._tv.insert(
                    parent_iid, 'end',
                    text=f'{UNCHECKED}  📁  {name}/',
                    open=False,          # collapsed by default
                )
                self._checks[iid] = False
                self._paths[iid]  = full
                self._load_recursive(full, iid)

            else:
                if name in EXCLUDE_FILES:
                    continue
                if os.path.splitext(name)[1].lower() in EXCLUDE_EXTENSIONS:
                    continue
                iid = self._tv.insert(
                    parent_iid, 'end',
                    text=f'{UNCHECKED}  {_file_icon(name)}  {name}',
                )
                self._checks[iid] = False
                self._paths[iid]  = full

    # ── Toggle ─────────────────────────────────────────────────────────────────

    def _on_click(self, event) -> None:
        iid = self._tv.identify_row(event.y)
        if not iid:
            return
        new_state = not self._checks[iid]
        self._set(iid, new_state)
        self._propagate_down(iid, new_state)
        self._propagate_up(iid)
        self.on_change()

    def _set(self, iid: str, state: bool) -> None:
        self._checks[iid] = state
        text = self._tv.item(iid, 'text')
        mark = CHECKED if state else UNCHECKED
        # Replace only the first char (the checkbox symbol)
        self._tv.item(iid, text=mark + text[1:])

    def _propagate_down(self, iid: str, state: bool) -> None:
        for child in self._tv.get_children(iid):
            self._set(child, state)
            self._propagate_down(child, state)

    def _propagate_up(self, iid: str) -> None:
        parent = self._tv.parent(iid)
        if not parent:
            return
        children_states = [self._checks[c] for c in self._tv.get_children(parent)]
        self._set(parent, any(children_states))
        self._propagate_up(parent)

    # ── Bulk ───────────────────────────────────────────────────────────────────

    def select_all(self, state: bool) -> None:
        for iid in self._checks:
            self._set(iid, state)
        self.on_change()

    # ── Path collection ────────────────────────────────────────────────────────

    def get_selected_paths(self, base_path: str) -> list[str]:
        return [
            path for iid, path in self._paths.items()
            if self._checks.get(iid, False)
        ]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _file_icon(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return {
        '.py': '🐍', '.js': '🟨', '.ts': '🔷', '.tsx': '🔷', '.jsx': '🟨',
        '.cs': '🟣', '.json': '🗂', '.md': '📝', '.yml': '⚙', '.yaml': '⚙',
        '.sql': '🗃', '.sh': '⌨', '.html': '🌐', '.css': '🎨', '.scss': '🎨',
        '.dockerfile': '🐳', '.toml': '⚙', '.xml': '📋', '.vue': '💚',
        '.rs': '🦀', '.go': '🐹', '.kt': '🟠', '.swift': '🍊',
    }.get(ext, '📄')