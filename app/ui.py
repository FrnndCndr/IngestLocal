import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from app.tree import FileTree
from app.exporter import Exporter
from config import DEFAULT_EXPORT_NAME


class App:
    """Main application window. Wires together FileTree and Exporter."""

    def __init__(self, root: tk.Tk):
        self.root      = root
        self.root.title('IngestLocal - Content Selector')
        self.base_path = ''
        self.file_tree: FileTree | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill='both', expand=True)

        ttk.Button(frame, text='Select Folder', command=self._on_select_folder).pack(pady=10)

        tree_widget = ttk.Treeview(frame, show='tree')
        tree_widget.pack(fill='both', expand=True)

        self.file_tree = FileTree(tree_widget)
        tree_widget.bind('<Button-1>', self.file_tree.toggle)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=6)
        ttk.Button(
            btn_frame, text='Select All',
            command=lambda: self.file_tree.select_all(True),
        ).pack(side='left', padx=5)
        ttk.Button(
            btn_frame, text='Deselect All',
            command=lambda: self.file_tree.select_all(False),
        ).pack(side='left', padx=5)

        ttk.Button(frame, text='Export Selection', command=self._on_export).pack(pady=10)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_select_folder(self) -> None:
        path = filedialog.askdirectory(title='Select project folder')
        if not path:
            return
        self.base_path = path
        self.file_tree.load(path)

    def _on_export(self) -> None:
        if not self.base_path:
            messagebox.showinfo('No folder', 'Please select a project folder first.')
            return

        paths = self.file_tree.get_selected_paths(self.base_path)
        if not paths:
            messagebox.showinfo('Empty selection', 'No files or folders selected.')
            return

        filename = simpledialog.askstring(
            'Export filename',
            'Enter the output filename (no path needed):',
            initialvalue=DEFAULT_EXPORT_NAME,
            parent=self.root,
        )
        if filename is None:
            return

        exporter    = Exporter(self.base_path)
        output_path = exporter.export(paths, filename)
        messagebox.showinfo('Export complete', f'File saved to:\n{output_path}')