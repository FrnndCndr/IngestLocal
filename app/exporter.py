import os
from datetime import datetime

from config import (
    EXCLUDE_FOLDERS, EXCLUDE_FILES, EXCLUDE_EXTENSIONS,
    EXTENSION_LANG, CONTEXTS_DIR, DEFAULT_EXPORT_NAME,
)
from app.git_info import get_git_info


class Exporter:
    """
    Handles building and writing the markdown export file.
    """

    def __init__(self, base_path: str):
        self.base_path = base_path

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def export(self, paths: list[str], filename: str) -> str:
        """
        Write the markdown file with summary, directory structure, and
        file contents. Returns the absolute path of the written file.
        """
        filename = self._ensure_md(filename)
        output_dir = os.path.join(os.getcwd(), CONTEXTS_DIR)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self._build_summary(paths))
            f.write('\n')
            f.write(self._build_directory_structure())
            f.write(self._build_files_content(paths))

        return output_path

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _build_summary(self, paths: list[str]) -> str:
        files = [p for p in paths if os.path.isfile(p)]
        token_estimate = self._estimate_tokens(files)
        git = get_git_info(self.base_path)

        project  = os.path.basename(self.base_path)
        exported = datetime.now().strftime('%Y-%m-%d %H:%M')

        rows = [
            ('**Project**',     f'`{project}`'),
            ('**Exported**',    exported),
            ('**Files**',       str(len(files))),
            ('**Est. tokens**', f'~{token_estimate:,}'),
        ]

        if git.get('branch'):
            rows.append(('**Branch**',      f"`{git['branch']}`"))
        if git.get('commit_hash'):
            rows.append(('**Last commit**', f"`{git['commit_hash']}` — {git['commit_msg']}"))
        if git.get('commit_date'):
            rows.append(('**Commit date**', git['commit_date']))

        col_width = max(len(r[0]) for r in rows)
        header    = f"| {'Field':<{col_width}} | Value |"
        separator = f"|{'-' * (col_width + 2)}|-------|"
        table_rows = '\n'.join(f"| {k:<{col_width}} | {v} |" for k, v in rows)

        return f"## Summary\n\n{header}\n{separator}\n{table_rows}\n"

    def _estimate_tokens(self, files: list[str]) -> int:
        total = 0
        for path in files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    total += len(f.read())
            except Exception:
                pass
        return total // 4

    # ------------------------------------------------------------------
    # Directory structure
    # ------------------------------------------------------------------

    def _build_directory_structure(self) -> str:
        tree_text = self._walk_directory(self.base_path)
        return f"## Directory Structure\n\n```\n{tree_text}```\n"

    def _walk_directory(self, path: str, level: int = 0) -> str:
        output = ''
        prefix = '│   ' * level + '├── '
        try:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                if name in EXCLUDE_FOLDERS:
                    continue
                if os.path.isdir(full):
                    output += f'{prefix}{name}/\n'
                    output += self._walk_directory(full, level + 1)
                else:
                    if name in EXCLUDE_FILES:
                        continue
                    if os.path.splitext(name)[1].lower() in EXCLUDE_EXTENSIONS:
                        continue
                    output += f'{prefix}{name}\n'
        except Exception:
            pass
        return output

    # ------------------------------------------------------------------
    # Files content
    # ------------------------------------------------------------------

    def _build_files_content(self, paths: list[str]) -> str:
        output = '\n## Files Content\n'
        for path in paths:
            if not os.path.isfile(path):
                continue
            rel = os.path.relpath(path, self.base_path)
            output += f'\n### `{rel}`\n\n'
            output += self._render_file(path)
        return output

    def _render_file(self, path: str) -> str:
        ext  = os.path.splitext(path)[1].lower()
        lang = EXTENSION_LANG.get(ext, '')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.endswith('\n'):
                content += '\n'
            return f'```{lang}\n{content}```\n'
        except Exception:
            return '> ⚠️ Could not read this file.\n'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_md(name: str) -> str:
        name = name.strip() or DEFAULT_EXPORT_NAME
        if not os.path.splitext(name)[1]:
            name += '.md'
        return name