import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.tree import FileTree
from app.exporter import Exporter
from app.git_info import get_git_info
from config import DEFAULT_EXPORT_NAME, EXTENSION_LANG

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

SIDEBAR_MIN     = 160
SIDEBAR_MAX     = 500
SIDEBAR_DEFAULT = 220
PREVIEW_CHAR_LIMIT = 80_000


class App:
    def __init__(self, root: ctk.CTk):
        self.root      = root
        self.base_path = ''
        self.file_tree: FileTree | None = None
        self._drag_x   = 0
        self._drag_w   = 0
        self._preview_job: str | None = None
        self._build_ui()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.title('IngestLocal')
        self.root.configure(fg_color=BG)

        outer = ctk.CTkFrame(self.root, fg_color='transparent')
        outer.pack(fill='both', expand=True)

        self._side    = self._build_sidebar(outer)
        self._divider = self._build_divider(outer)
        self._main    = self._build_main(outer)

        self._side.pack(side='left', fill='y')
        self._divider.pack(side='left', fill='y')
        self._main.pack(side='left', fill='both', expand=True)

    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent) -> ctk.CTkFrame:
        side = ctk.CTkFrame(parent, fg_color=SIDE, corner_radius=0,
                            width=SIDEBAR_DEFAULT, border_width=1, border_color=BORDER)
        side.pack_propagate(False)

        hdr = ctk.CTkFrame(side, fg_color='transparent')
        hdr.pack(fill='x', padx=10, pady=(12, 4))
        ctk.CTkButton(
            hdr, text='  📂  Select Folder',
            fg_color=CARD, hover_color=BORDER, text_color=TEXT,
            corner_radius=8, height=32, font=ctk.CTkFont(size=13),
            command=self._on_select_folder,
        ).pack(fill='x')

        self._path_label = ctk.CTkLabel(
            side, text='No folder selected', text_color=MUTED,
            font=ctk.CTkFont(size=11), anchor='w',
        )
        self._path_label.pack(fill='x', padx=14, pady=(0, 6))

        tree_container = ctk.CTkFrame(side, fg_color='transparent')
        tree_container.pack(fill='both', expand=True, padx=0, pady=0)
        self.file_tree = FileTree(tree_container, on_change=self._on_selection_change)

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

        return side

    # ── Drag divider ───────────────────────────────────────────────────────────

    def _build_divider(self, parent) -> ctk.CTkFrame:
        div = ctk.CTkFrame(parent, fg_color=BORDER, corner_radius=0, width=4)
        div.pack_propagate(False)
        div.configure(cursor='sb_h_double_arrow')
        div.bind('<ButtonPress-1>', self._on_drag_start)
        div.bind('<B1-Motion>',     self._on_drag_move)
        div.bind('<Enter>', lambda e: div.configure(fg_color=BLUE))
        div.bind('<Leave>', lambda e: div.configure(fg_color=BORDER))
        return div

    def _on_drag_start(self, event) -> None:
        self._drag_x = event.x_root
        self._drag_w = self._side.winfo_width()

    def _on_drag_move(self, event) -> None:
        new_w = self._drag_w + (event.x_root - self._drag_x)
        self._side.configure(width=max(SIDEBAR_MIN, min(SIDEBAR_MAX, new_w)))

    # ── Main panel ─────────────────────────────────────────────────────────────

    def _build_main(self, parent) -> ctk.CTkFrame:
        main = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        main.rowconfigure(0, weight=1)
        main.rowconfigure(1, weight=0)
        main.columnconfigure(0, weight=1)

        # Vertical PanedWindow — top row vs files content, fully responsive
        vpane = tk.PanedWindow(
            main, orient='vertical',
            bg=BORDER, sashwidth=4, sashrelief='flat',
            handlesize=0, bd=0,
        )
        vpane.grid(row=0, column=0, sticky='nsew')

        # Top: Summary (left) + Directory Structure (right)
        top = ctk.CTkFrame(vpane, fg_color=BG)
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        self._pane_summary = self._build_text_pane(
            top, 'Summary', row=0, col=0, hsb=False)
        self._pane_structure = self._build_text_pane(
            top, 'Directory Structure', row=0, col=1, hsb=False)

        # Bottom: Files content
        bottom = ctk.CTkFrame(vpane, fg_color=BG)
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure(0, weight=1)

        self._pane_content = self._build_text_pane(
            bottom, 'Files Content', row=0, col=0, hsb=True)

        vpane.add(top,    minsize=120)
        vpane.add(bottom, minsize=80)

        # Place sash at ~28% once the window has rendered
        main.after(150, lambda: vpane.sash_place(0, 0, int(vpane.winfo_height() * 0.28)))

        # Footer
        self._build_footer(main, row=1)

        return main

    # ── Pane builder ───────────────────────────────────────────────────────────

    def _build_text_pane(
        self, parent, title: str,
        row: int, col: int,
        colspan: int = 1,
        hsb: bool = False,
    ) -> tk.Text:
        wrapper = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8,
                               border_width=1, border_color=BORDER)
        wrapper.grid(row=row, column=col, columnspan=colspan,
                     sticky='nsew', padx=6, pady=6)
        wrapper.rowconfigure(1, weight=1)
        wrapper.columnconfigure(0, weight=1)

        # Header: title left, Copy button right
        header = ctk.CTkFrame(wrapper, fg_color='transparent')
        header.grid(row=0, column=0, columnspan=2, sticky='ew', padx=6, pady=(6, 2))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=title.upper(),
            text_color=MUTED, font=ctk.CTkFont(size=10),
            anchor='w',
        ).grid(row=0, column=0, sticky='w', padx=4)

        copy_btn = ctk.CTkLabel(
            header, text='⎘  Copy',
            text_color=MUTED, font=ctk.CTkFont(size=10),
            cursor='hand2',
        )
        copy_btn.grid(row=0, column=1, sticky='e', padx=4)

        txt = tk.Text(
            wrapper,
            bg=CARD, fg=MUTED,
            insertbackground=BLUE,
            selectbackground=BORDER,
            font=('Consolas', 10),
            relief='flat', bd=0,
            padx=10, pady=6,
            wrap='none',
            state='disabled',
            cursor='arrow',
        )
        txt.grid(row=1, column=0, sticky='nsew')

        vsb = ctk.CTkScrollbar(wrapper, command=txt.yview,
                               button_color=BORDER, button_hover_color=MUTED)
        vsb.grid(row=1, column=1, sticky='ns')
        txt.configure(yscrollcommand=vsb.set)

        if hsb:
            hbar = ctk.CTkScrollbar(wrapper, command=txt.xview,
                                    button_color=BORDER, button_hover_color=MUTED,
                                    orientation='horizontal')
            hbar.grid(row=2, column=0, sticky='ew')
            txt.configure(xscrollcommand=hbar.set)

        # Tags
        txt.tag_configure('key',         foreground=MUTED,     font=('Consolas', 10))
        txt.tag_configure('value',       foreground=TEXT,       font=('Consolas', 10))
        txt.tag_configure('blue',        foreground=BLUE,       font=('Consolas', 10, 'bold'))
        txt.tag_configure('green',       foreground=GREEN,      font=('Consolas', 10, 'bold'))
        txt.tag_configure('amber',       foreground=AMBER,      font=('Consolas', 10, 'bold'))
        txt.tag_configure('filepath',    foreground=BLUE,       font=('Consolas', 10, 'bold'))
        txt.tag_configure('fence',       foreground=BORDER,     font=('Consolas', 10))
        txt.tag_configure('code',        foreground='#A8FF78',  font=('Consolas', 10))
        txt.tag_configure('truncated',   foreground=AMBER)
        txt.tag_configure('placeholder', foreground=BORDER,     font=('Consolas', 10, 'italic'))

        # Wire up copy button
        def do_copy(event=None, t=txt, btn=copy_btn):
            self._copy_pane(t, btn)
        copy_btn.bind('<Button-1>', do_copy)
        copy_btn.bind('<Enter>', lambda e, b=copy_btn: b.configure(text_color=TEXT))
        copy_btn.bind('<Leave>', lambda e, b=copy_btn: b.configure(text_color=MUTED))

        return txt

    # ── Copy helper ────────────────────────────────────────────────────────────

    def _copy_pane(self, txt: tk.Text, btn: ctk.CTkLabel) -> None:
        """Copy all text from a pane to the clipboard and flash the button."""
        content = txt.get('1.0', 'end').strip()
        if not content:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

        # Flash "Copied!" for 1.5s then revert
        btn.configure(text='✓  Copied!', text_color=GREEN)
        self.root.after(1500, lambda: btn.configure(text='⎘  Copy', text_color=MUTED))

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self, parent, row: int) -> None:
        footer = ctk.CTkFrame(parent, fg_color=SIDE, corner_radius=0,
                              border_width=1, border_color=BORDER, height=52)
        footer.grid(row=row, column=0, columnspan=1, sticky='ew')
        footer.pack_propagate(False)

        inner = ctk.CTkFrame(footer, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=12, pady=8)
        inner.columnconfigure(0, weight=1)

        self._filename_entry = ctk.CTkEntry(
            inner, placeholder_text=DEFAULT_EXPORT_NAME,
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
            corner_radius=8, height=34, font=ctk.CTkFont(size=13),
        )
        self._filename_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))

        ctk.CTkButton(
            inner, text='Export', width=90,
            fg_color=BLUE, hover_color='#0071E3', text_color='white',
            corner_radius=8, height=34, font=ctk.CTkFont(size=13, weight='bold'),
            command=self._on_export,
        ).grid(row=0, column=1)

    # ── Pane writers ───────────────────────────────────────────────────────────

    def _write_pane(self, pane: tk.Text, chunks: list[tuple[str, str]]) -> None:
        pane.configure(state='normal')
        pane.delete('1.0', 'end')
        for text, tag in chunks:
            pane.insert('end', text, tag)
        pane.configure(state='disabled')
        pane.yview_moveto(0)

    # ── Preview build (threaded) ────────────────────────────────────────────────

    def _update_preview(self, paths: list[str]) -> None:
        def build():
            files            = [p for p in paths if os.path.isfile(p)]
            summary_chunks   = self._build_summary_chunks(files)
            structure_chunks = self._build_structure_chunks()
            content_chunks   = self._build_content_chunks(files)

            self.root.after(0, lambda: (
                self._write_pane(self._pane_summary,   summary_chunks),
                self._write_pane(self._pane_structure, structure_chunks),
                self._write_pane(self._pane_content,   content_chunks),
            ))

        threading.Thread(target=build, daemon=True).start()

    def _build_summary_chunks(self, files: list[str]) -> list[tuple[str, str]]:
        if not files:
            return [('No files selected\n', 'placeholder')]

        tokens = sum(
            len(open(p, encoding='utf-8', errors='ignore').read()) for p in files
        ) // 4
        git = get_git_info(self.base_path)
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        rows: list[tuple[str, str, str]] = [
            ('Project',     os.path.basename(self.base_path), 'value'),
            ('Exported',    now,                               'value'),
            ('Files',       str(len(files)),                   'green'),
            ('Est. tokens', f'~{tokens:,}',                   'amber'),
        ]
        if git.get('branch'):
            rows.append(('Branch', git['branch'], 'blue'))
        if git.get('commit_hash'):
            rows.append(('Commit', git['commit_hash'], 'blue'))
        if git.get('commit_msg'):
            rows.append(('Message', git['commit_msg'], 'value'))

        col = max(len(r[0]) for r in rows) + 2
        chunks: list[tuple[str, str]] = []
        for label, val, tag in rows:
            chunks.append((f'{label:<{col}}', 'key'))
            chunks.append((val + '\n', tag))
        return chunks

    def _build_structure_chunks(self) -> list[tuple[str, str]]:
        if not self.base_path:
            return [('No folder selected\n', 'placeholder')]
        exp  = Exporter(self.base_path)
        text = exp._walk_directory(self.base_path)
        return [(text or '(empty)\n', 'value')]

    def _build_content_chunks(self, files: list[str]) -> list[tuple[str, str]]:
        if not files:
            return [('No files selected\n', 'placeholder')]

        chunks: list[tuple[str, str]] = []
        total_chars = 0

        for path in files:
            if total_chars >= PREVIEW_CHAR_LIMIT:
                remaining = len(files) - files.index(path)
                chunks.append((
                    f'\n... {remaining} more file(s) not shown '
                    f'(preview limit {PREVIEW_CHAR_LIMIT:,} chars)\n',
                    'truncated',
                ))
                break

            rel  = os.path.relpath(path, self.base_path)
            ext  = os.path.splitext(path)[1].lower()
            lang = EXTENSION_LANG.get(ext, '')

            chunks.append((f'### `{rel}`\n', 'filepath'))
            chunks.append((f'```{lang}\n',   'fence'))

            try:
                content = open(path, encoding='utf-8', errors='ignore').read()
                total_chars += len(content)
                if not content.endswith('\n'):
                    content += '\n'
                chunks.append((content, 'code'))
            except Exception:
                chunks.append(('> ⚠️  Could not read file.\n', 'key'))

            chunks.append(('```\n\n', 'fence'))

        return chunks

    # ── Selection change ───────────────────────────────────────────────────────

    def _on_selection_change(self) -> None:
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(300, self._trigger_preview)

    def _trigger_preview(self) -> None:
        self._preview_job = None
        paths = self.file_tree.get_selected_paths(self.base_path)
        self._update_preview(paths)

    def _load_git_stats(self) -> None:
        pass   # git info now shown inside summary panel only

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
        self._on_selection_change()

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