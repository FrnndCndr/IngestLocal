import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.tree import FileTree
from app.exporter import Exporter
from app.git_info import get_git_info
from config import DEFAULT_EXPORT_NAME

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

BLUE   = '#0A84FF'
BG     = '#111113'
SIDE   = '#1C1C1E'
CARD   = '#2C2C2E'
BORDER = '#3A3A3C'
TEXT   = '#F2F2F7'
MUTED  = '#8E8E93'
GREEN  = '#30D158'
AMBER  = '#FFD60A'


class App:
    def __init__(self, root: ctk.CTk):
        self.root      = root
        self.base_path = ''
        self.file_tree: FileTree | None = None
        self._build_ui()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.title('IngestLocal')
        self.root.configure(fg_color=BG)

        outer = ctk.CTkFrame(self.root, fg_color='transparent')
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        self._build_sidebar(outer)
        self._build_main(outer)

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent) -> None:
        side = ctk.CTkFrame(parent, fg_color=SIDE, corner_radius=0,
                            width=220, border_width=1, border_color=BORDER)
        side.grid(row=0, column=0, sticky='nsew')
        side.pack_propagate(False)

        # Select folder button
        hdr = ctk.CTkFrame(side, fg_color='transparent')
        hdr.pack(fill='x', padx=10, pady=(12, 4))
        ctk.CTkButton(
            hdr, text='  📂  Select Folder',
            fg_color=CARD, hover_color=BORDER, text_color=TEXT,
            corner_radius=8, height=32, font=ctk.CTkFont(size=13),
            command=self._on_select_folder,
        ).pack(fill='x')

        # Current path label
        self._path_label = ctk.CTkLabel(
            side, text='No folder selected', text_color=MUTED,
            font=ctk.CTkFont(size=11), anchor='w',
        )
        self._path_label.pack(fill='x', padx=14, pady=(0, 6))

        # Tree container — plain CTkFrame, scroll handled by Treeview internally
        tree_container = ctk.CTkFrame(side, fg_color='transparent')
        tree_container.pack(fill='both', expand=True)
        self.file_tree = FileTree(tree_container, on_change=self._refresh_stats)

        # Select / Deselect all
        ftr = ctk.CTkFrame(side, fg_color='transparent')
        ftr.pack(fill='x', padx=10, pady=(4, 12))
        ftr.columnconfigure((0, 1), weight=1)

        btn_kw = dict(fg_color=CARD, hover_color=BORDER, text_color=TEXT,
                      corner_radius=8, height=28, font=ctk.CTkFont(size=12))
        ctk.CTkButton(ftr, text='Select All',
                      command=lambda: self.file_tree.select_all(True),
                      **btn_kw).grid(row=0, column=0, padx=(0, 4), sticky='ew')
        ctk.CTkButton(ftr, text='Deselect All',
                      command=lambda: self.file_tree.select_all(False),
                      **btn_kw).grid(row=0, column=1, padx=(4, 0), sticky='ew')

    # ── Main panel ─────────────────────────────────────────────────────────────

    def _build_main(self, parent) -> None:
        main = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky='nsew')
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)

        # Stats bar
        stats_bar = ctk.CTkFrame(main, fg_color=SIDE, corner_radius=0,
                                 border_width=1, border_color=BORDER, height=54)
        stats_bar.grid(row=0, column=0, sticky='ew')
        stats_bar.pack_propagate(False)

        inner = ctk.CTkFrame(stats_bar, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=16, pady=6)

        self._stat_branch = self._stat_block(inner, 'Branch',      '—',       BLUE)
        self._stat_commit = self._stat_block(inner, 'Last commit',  '—',       TEXT)
        self._stat_files  = self._stat_block(inner, 'Selected',     '0 files', GREEN)
        self._stat_tokens = self._stat_block(inner, 'Est. tokens',  '—',       AMBER)
        for w in (self._stat_branch, self._stat_commit, self._stat_files, self._stat_tokens):
            w.pack(side='left', padx=(0, 24))

        # Empty state hint
        self._empty_label = ctk.CTkLabel(
            main, text='Select a folder to get started',
            text_color=MUTED, font=ctk.CTkFont(size=14),
        )
        self._empty_label.grid(row=1, column=0)

        # Footer
        footer = ctk.CTkFrame(main, fg_color=SIDE, corner_radius=0,
                              border_width=1, border_color=BORDER, height=52)
        footer.grid(row=2, column=0, sticky='ew')
        footer.pack_propagate(False)

        foot_inner = ctk.CTkFrame(footer, fg_color='transparent')
        foot_inner.pack(fill='both', expand=True, padx=12, pady=8)
        foot_inner.columnconfigure(0, weight=1)

        self._filename_entry = ctk.CTkEntry(
            foot_inner, placeholder_text=DEFAULT_EXPORT_NAME,
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34, font=ctk.CTkFont(size=13),
        )
        self._filename_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))

        ctk.CTkButton(
            foot_inner, text='Export', width=90,
            fg_color=BLUE, hover_color='#0071E3', text_color='white',
            corner_radius=8, height=34, font=ctk.CTkFont(size=13, weight='bold'),
            command=self._on_export,
        ).grid(row=0, column=1)

    def _stat_block(self, parent, label: str, value: str, color: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        ctk.CTkLabel(frame, text=label.upper(), text_color=MUTED,
                     font=ctk.CTkFont(size=10)).pack(anchor='w')
        val = ctk.CTkLabel(frame, text=value, text_color=color,
                           font=ctk.CTkFont(size=13, weight='bold'))
        val.pack(anchor='w')
        frame._val_label = val
        return frame

    # ── Stats refresh ──────────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        if not self.base_path:
            return
        paths  = self.file_tree.get_selected_paths(self.base_path)
        files  = [p for p in paths if os.path.isfile(p)]
        tokens = sum(
            len(open(p, encoding='utf-8', errors='ignore').read())
            for p in files
        ) // 4
        self._stat_files._val_label.configure(
            text=f'{len(files)} file{"s" if len(files) != 1 else ""}')
        self._stat_tokens._val_label.configure(
            text=f'~{tokens:,}' if tokens else '—')

    def _load_git_stats(self) -> None:
        git = get_git_info(self.base_path)
        self._stat_branch._val_label.configure(text=git.get('branch', '—'))
        msg      = git.get('commit_msg', '')
        short    = (msg[:26] + '…') if len(msg) > 26 else msg
        self._stat_commit._val_label.configure(
            text=f"{git.get('commit_hash', '—')}  {short}".strip())

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_select_folder(self) -> None:
        path = filedialog.askdirectory(title='Select project folder')
        if not path:
            return
        self.base_path = path
        home    = os.path.expanduser('~')
        display = ('~/' + os.path.relpath(path, home)) if path.startswith(home) else path
        self._path_label.configure(text=display)
        self.file_tree.load(path)
        self._load_git_stats()
        self._refresh_stats()
        self._empty_label.grid_remove()

    def _on_export(self) -> None:
        if not self.base_path:
            messagebox.showinfo('No folder', 'Please select a project folder first.')
            return
        paths = self.file_tree.get_selected_paths(self.base_path)
        if not paths:
            messagebox.showinfo('Empty selection', 'No files or folders selected.')
            return
        filename    = self._filename_entry.get().strip() or DEFAULT_EXPORT_NAME
        exporter    = Exporter(self.base_path)
        output_path = exporter.export(paths, filename)
        messagebox.showinfo('Export complete', f'Saved to:\n{output_path}')