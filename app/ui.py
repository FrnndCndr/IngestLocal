import os
import threading
import tkinter as tk
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
RED    = '#FF453A'

SIDEBAR_MIN     = 160
SIDEBAR_MAX     = 500
SIDEBAR_DEFAULT = 220

# Max chars rendered in preview (keeps it snappy for huge selections)
PREVIEW_CHAR_LIMIT = 80_000


class App:
    def __init__(self, root: ctk.CTk):
        self.root        = root
        self.base_path   = ''
        self.file_tree: FileTree | None = None
        self._drag_x     = 0
        self._drag_w     = 0
        self._preview_job: str | None = None   # after() handle for debounce
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

        # Preview area
        self._build_preview(main)

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

        return main

    # ── Preview ────────────────────────────────────────────────────────────────

    def _build_preview(self, parent) -> None:
        container = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        container.grid(row=1, column=0, sticky='nsew')
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Native tk.Text — much faster than CTkTextbox for large content
        self._preview = tk.Text(
            container,
            bg=BG, fg=MUTED,
            insertbackground=BLUE,
            selectbackground=BORDER,
            font=('Cascadia Code', 11) if self._font_exists('Cascadia Code')
                 else ('Consolas', 11),
            relief='flat', bd=0,
            padx=16, pady=12,
            wrap='none',
            state='disabled',
            cursor='arrow',
        )
        self._preview.grid(row=0, column=0, sticky='nsew')

        # Scrollbars
        vsb = ctk.CTkScrollbar(container, command=self._preview.yview,
                               button_color=BORDER, button_hover_color=MUTED)
        vsb.grid(row=0, column=1, sticky='ns')
        hsb = ctk.CTkScrollbar(container, command=self._preview.xview,
                               button_color=BORDER, button_hover_color=MUTED,
                               orientation='horizontal')
        hsb.grid(row=1, column=0, sticky='ew')
        self._preview.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Text tags for highlighting
        self._preview.tag_configure('heading',  foreground=TEXT,  font=('Consolas', 11, 'bold'))
        self._preview.tag_configure('h3',       foreground=MUTED, font=('Consolas', 10, 'italic'))
        self._preview.tag_configure('fence',    foreground=BORDER)
        self._preview.tag_configure('code',     foreground='#A8FF78', font=('Consolas', 11))
        self._preview.tag_configure('filepath', foreground=BLUE,  font=('Consolas', 11, 'bold'))
        self._preview.tag_configure('muted',    foreground=MUTED)
        self._preview.tag_configure('truncated',foreground=AMBER)
        self._preview.tag_configure('empty',    foreground=MUTED, font=('Consolas', 13))

        self._set_preview_placeholder()

    @staticmethod
    def _font_exists(name: str) -> bool:
        try:
            import tkinter.font as tkfont
            return name in tkfont.families()
        except Exception:
            return False

    def _set_preview_placeholder(self) -> None:
        self._preview_write('Select files to preview the output\n', 'empty')

    def _preview_write(self, text: str, *tags) -> None:
        self._preview.configure(state='normal')
        self._preview.delete('1.0', 'end')
        self._preview.insert('end', text, tags)
        self._preview.configure(state='disabled')

    def _update_preview(self, paths: list[str]) -> None:
        """Build preview content in a thread, then update the widget on the main thread."""
        def build():
            files  = [p for p in paths if os.path.isfile(p)]
            chunks: list[tuple[str, str]] = []   # (text, tag)

            if not files:
                chunks.append(('No files selected\n', 'empty'))
                self.root.after(0, lambda c=chunks: self._render_preview(c))
                return

            # Summary block
            chunks.append(('## Summary\n', 'heading'))
            chunks.append((f'   {len(files)} files selected\n\n', 'muted'))

            # Directory structure header
            chunks.append(('## Directory Structure\n\n', 'heading'))
            chunks.append(('```\n', 'fence'))
            struct = self._build_structure_preview()
            chunks.append((struct, 'muted'))
            chunks.append(('```\n\n', 'fence'))

            # Files content
            chunks.append(('## Files Content\n\n', 'heading'))

            total_chars = 0
            for path in files:
                if total_chars >= PREVIEW_CHAR_LIMIT:
                    remaining = len(files) - files.index(path)
                    chunks.append((
                        f'\n... {remaining} more file(s) not shown in preview '
                        f'(limit {PREVIEW_CHAR_LIMIT:,} chars)\n', 'truncated'
                    ))
                    break

                rel = os.path.relpath(path, self.base_path)
                chunks.append((f'### `{rel}`\n', 'filepath'))

                try:
                    content = open(path, encoding='utf-8', errors='ignore').read()
                    total_chars += len(content)
                    ext  = os.path.splitext(path)[1].lower()
                    lang = _EXT_LANG.get(ext, '')
                    chunks.append((f'```{lang}\n', 'fence'))
                    chunks.append((content if content.endswith('\n') else content + '\n', 'code'))
                    chunks.append(('```\n\n', 'fence'))
                except Exception:
                    chunks.append(('> ⚠️  Could not read file.\n\n', 'muted'))

            self.root.after(0, lambda c=chunks: self._render_preview(c))

        threading.Thread(target=build, daemon=True).start()

    def _build_structure_preview(self) -> str:
        """Quick directory structure string (reuses exporter logic)."""
        from app.exporter import Exporter
        exp = Exporter(self.base_path)
        return exp._walk_directory(self.base_path)

    def _render_preview(self, chunks: list[tuple[str, str]]) -> None:
        self._preview.configure(state='normal')
        self._preview.delete('1.0', 'end')
        for text, tag in chunks:
            self._preview.insert('end', text, tag)
        self._preview.configure(state='disabled')
        self._preview.yview_moveto(0)

    # ── Stat helpers ───────────────────────────────────────────────────────────

    def _stat_block(self, parent, label: str, value: str, color: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        ctk.CTkLabel(frame, text=label.upper(), text_color=MUTED,
                     font=ctk.CTkFont(size=10)).pack(anchor='w')
        val = ctk.CTkLabel(frame, text=value, text_color=color,
                           font=ctk.CTkFont(size=13, weight='bold'))
        val.pack(anchor='w')
        frame._val_label = val
        return frame

    # ── Selection change (debounced) ───────────────────────────────────────────

    def _on_selection_change(self) -> None:
        self._refresh_stats()
        # Debounce: wait 300ms after last change before rebuilding preview
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(300, self._trigger_preview)

    def _trigger_preview(self) -> None:
        self._preview_job = None
        paths = self.file_tree.get_selected_paths(self.base_path)
        self._update_preview(paths)

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
        msg   = git.get('commit_msg', '')
        short = (msg[:26] + '…') if len(msg) > 26 else msg
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


# ── Extension → markdown lang map (local copy for preview) ────────────────────
_EXT_LANG = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.tsx': 'tsx', '.jsx': 'jsx', '.cs': 'csharp', '.html': 'html',
    '.css': 'css', '.scss': 'scss', '.json': 'json', '.yaml': 'yaml',
    '.yml': 'yaml', '.md': 'markdown', '.sql': 'sql', '.sh': 'bash',
    '.xml': 'xml', '.toml': 'toml', '.vue': 'vue', '.rs': 'rust',
    '.go': 'go', '.kt': 'kotlin', '.swift': 'swift',
}