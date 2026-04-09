import os
from tkinter import ttk

from config import EXCLUDE_FOLDERS, EXCLUDE_FILES, EXCLUDE_EXTENSIONS


class FileTree:
    """
    Manages the Treeview widget: loading the directory tree,
    handling checkbox toggles, and collecting selected paths.
    """

    CHECKED   = '[✔]'
    UNCHECKED = '[ ]'

    def __init__(self, tree: ttk.Treeview):
        self.tree   = tree
        self.checks: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, path: str) -> None:
        """Clear the tree and populate it from `path`."""
        self.tree.delete(*self.tree.get_children())
        self.checks.clear()
        self._load_recursive(path, '')

    def _load_recursive(self, path: str, parent: str) -> None:
        try:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)

                if name in EXCLUDE_FOLDERS:
                    continue

                if os.path.isdir(full):
                    node = self.tree.insert(parent, 'end', text=f'{self.UNCHECKED} {name}/', open=False)
                    self.checks[node] = False
                    self._load_recursive(full, node)
                else:
                    if name in EXCLUDE_FILES:
                        continue
                    if os.path.splitext(name)[1].lower() in EXCLUDE_EXTENSIONS:
                        continue
                    node = self.tree.insert(parent, 'end', text=f'{self.UNCHECKED} {name}')
                    self.checks[node] = False

        except PermissionError:
            pass

    # ------------------------------------------------------------------
    # Toggle & propagation
    # ------------------------------------------------------------------

    def toggle(self, event) -> None:
        """Handle a click event on the tree: flip the checkbox of the clicked row."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        new_state = not self.checks.get(item, False)
        self._set_item(item, new_state)
        self._propagate_to_children(item, new_state)
        self._update_parents(item)

    def select_all(self, state: bool) -> None:
        """Set all nodes to `state`."""
        for item in self.tree.get_children():
            self._set_item(item, state)
            self._propagate_to_children(item, state)

    def _set_item(self, item: str, state: bool) -> None:
        text  = self.tree.item(item, 'text')
        name  = text[4:]  # strip the '[✔] ' or '[ ] ' prefix
        mark  = self.CHECKED if state else self.UNCHECKED
        self.tree.item(item, text=f'{mark} {name}')
        self.checks[item] = state

    def _propagate_to_children(self, item: str, state: bool) -> None:
        for child in self.tree.get_children(item):
            self._set_item(child, state)
            self._propagate_to_children(child, state)

    def _update_parents(self, item: str) -> None:
        parent = self.tree.parent(item)
        if not parent:
            return
        children_states = [self.checks[c] for c in self.tree.get_children(parent)]
        self._set_item(parent, any(children_states))
        self._update_parents(parent)

    # ------------------------------------------------------------------
    # Selection retrieval
    # ------------------------------------------------------------------

    def get_selected_paths(self, base_path: str) -> list[str]:
        """Return a flat list of absolute paths for all checked nodes."""
        selected = []

        def walk(item: str, current_path: str) -> None:
            text = self.tree.item(item, 'text')
            name = text[4:].rstrip('/')
            full = os.path.join(current_path, name)
            if self.checks.get(item, False):
                selected.append(full)
            for child in self.tree.get_children(item):
                walk(child, full)

        for root_item in self.tree.get_children():
            walk(root_item, base_path)

        return selected