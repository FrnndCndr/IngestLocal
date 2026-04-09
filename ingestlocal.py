import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from datetime import datetime

# Filtros
EXCLUIR_CARPETAS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'env', '.env', '.tox', 'build', 'dist', '.pytest_cache', '.angular'
}
EXCLUIR_ARCHIVOS = {
    '.env', 'package-lock.json', 'poetry.lock', 'Pipfile.lock', '.coverage'
}
EXTENSIONES_EXCLUIDAS = {
    '.pyc', '.exe', '.dll', '.so', '.zip', '.tar', '.gz', '.rar',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
    '.mp3', '.mp4', '.mov', '.avi', '.flv', '.webm'
}

# Mapa extensión -> lenguaje para markdown code fences
EXTENSION_LANG = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.jsx': 'jsx', '.tsx': 'tsx', '.html': 'html', '.css': 'css',
    '.scss': 'scss', '.sass': 'sass', '.json': 'json',
    '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown',
    '.sql': 'sql', '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
    '.cs': 'csharp', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
    '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
    '.xml': 'xml', '.toml': 'toml', '.ini': 'ini',
    '.tf': 'hcl', '.dockerfile': 'dockerfile', '.vue': 'vue',
    '.svelte': 'svelte', '.kt': 'kotlin', '.swift': 'swift',
}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("GitIngest Local - Selector de Contenido")
        self.ruta_base = ''
        self.tree = None
        self.checks = {}
        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill='both', expand=True)

        ttk.Button(frame, text="Seleccionar Carpeta", command=self.seleccionar_carpeta).pack(pady=10)

        self.tree = ttk.Treeview(frame, show='tree')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind("<Button-1>", self.toggle_checkbox)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=6)
        ttk.Button(
            btn_frame,
            text="Seleccionar todo",
            command=lambda: self.seleccionar_deseleccionar_todo(True)
        ).pack(side='left', padx=5)
        ttk.Button(
            btn_frame,
            text="Deseleccionar todo",
            command=lambda: self.seleccionar_deseleccionar_todo(False)
        ).pack(side='left', padx=5)

        ttk.Button(frame, text="Exportar Selección", command=self.exportar).pack(pady=10)

    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory(title="Selecciona la carpeta del proyecto")
        if not ruta:
            return
        self.ruta_base = ruta
        self.tree.delete(*self.tree.get_children())
        self.checks.clear()
        self.cargar_arbol(self.ruta_base, '')

    def cargar_arbol(self, path, parent):
        try:
            for item in sorted(os.listdir(path)):
                ruta = os.path.join(path, item)
                if item in EXCLUIR_CARPETAS:
                    continue
                if os.path.isdir(ruta):
                    nodo = self.tree.insert(parent, 'end', text=f"[ ] {item}/", open=False)
                    self.checks[nodo] = False
                    self.cargar_arbol(ruta, nodo)
                else:
                    if item in EXCLUIR_ARCHIVOS:
                        continue
                    ext = os.path.splitext(item)[1].lower()
                    if ext in EXTENSIONES_EXCLUIDAS:
                        continue
                    nodo = self.tree.insert(parent, 'end', text=f"[ ] {item}")
                    self.checks[nodo] = False
        except PermissionError:
            pass

    def toggle_checkbox(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        estado = self.checks.get(item, False)
        nuevo_estado = not estado
        self.checks[item] = nuevo_estado
        self.actualizar_checkbox(item, nuevo_estado)
        self.propagar_a_hijos(item, nuevo_estado)
        self.actualizar_padres(item)

    def actualizar_checkbox(self, item, estado):
        texto = self.tree.item(item, 'text')
        nombre = texto[4:]
        nuevo_texto = f"[✔] {nombre}" if estado else f"[ ] {nombre}"
        self.tree.item(item, text=nuevo_texto)
        self.checks[item] = estado

    def propagar_a_hijos(self, item, estado):
        for hijo in self.tree.get_children(item):
            self.actualizar_checkbox(hijo, estado)
            self.propagar_a_hijos(hijo, estado)

    def actualizar_padres(self, item):
        padre = self.tree.parent(item)
        if not padre:
            return
        hijos = self.tree.get_children(padre)
        estados = [self.checks[h] for h in hijos]
        if all(estados):
            self.actualizar_checkbox(padre, True)
        elif any(estados):
            self.actualizar_checkbox(padre, True)
        else:
            self.actualizar_checkbox(padre, False)
        self.actualizar_padres(padre)

    def seleccionar_deseleccionar_todo(self, estado: bool):
        for item in self.tree.get_children():
            self.actualizar_checkbox(item, estado)
            self.propagar_a_hijos(item, estado)

    def obtener_seleccionados(self):
        seleccionados = []

        def recorrer(item, path):
            texto = self.tree.item(item, 'text')
            nombre = texto[4:].rstrip('/')
            ruta_actual = os.path.join(path, nombre)
            if self.checks.get(item, False):
                seleccionados.append(ruta_actual)
            for hijo in self.tree.get_children(item):
                recorrer(hijo, ruta_actual)

        for item in self.tree.get_children():
            recorrer(item, self.ruta_base)
        return seleccionados

    def generar_estructura(self, path, nivel=0):
        salida = ""
        prefijo = "│   " * nivel + "├── "
        try:
            items = sorted(os.listdir(path))
            for item in items:
                ruta = os.path.join(path, item)
                if item in EXCLUIR_CARPETAS:
                    continue
                if os.path.isdir(ruta):
                    salida += f"{prefijo}{item}/\n"
                    salida += self.generar_estructura(ruta, nivel + 1)
                else:
                    if item in EXCLUIR_ARCHIVOS:
                        continue
                    ext = os.path.splitext(item)[1].lower()
                    if ext in EXTENSIONES_EXCLUIDAS:
                        continue
                    salida += f"{prefijo}{item}\n"
        except Exception:
            pass
        return salida

    def obtener_git_info(self, path: str) -> dict:
        """Intenta leer branch y último commit del repo en `path`. Retorna dict con los campos disponibles."""
        info = {}
        try:
            branch = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if branch.returncode == 0:
                info['branch'] = branch.stdout.strip()

            log = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%s|%ad', '--date=format:%Y-%m-%d %H:%M'],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if log.returncode == 0 and log.stdout.strip():
                parts = log.stdout.strip().split('|', 2)
                info['commit_hash'] = parts[0][:7] if len(parts) > 0 else ''
                info['commit_msg']  = parts[1]         if len(parts) > 1 else ''
                info['commit_date'] = parts[2]         if len(parts) > 2 else ''
        except Exception:
            pass
        return info

    def generar_summary(self, paths: list) -> str:
        """Genera el bloque de summary en markdown."""
        # Contar solo archivos (no carpetas)
        archivos = [p for p in paths if os.path.isfile(p)]
        n_archivos = len(archivos)

        # Estimar tokens: leer contenido y dividir por 4
        total_chars = 0
        for p in archivos:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    total_chars += len(f.read())
            except Exception:
                pass
        tokens_estimados = total_chars // 4

        # Info git
        git = self.obtener_git_info(self.ruta_base)

        proyecto = os.path.basename(self.ruta_base)
        fecha    = datetime.now().strftime('%Y-%m-%d %H:%M')

        lineas = [
            "## Summary\n",
            f"| Campo            | Valor |",
            f"|------------------|-------|",
            f"| **Project**      | `{proyecto}` |",
            f"| **Exported**     | {fecha} |",
            f"| **Files**        | {n_archivos} |",
            f"| **Est. tokens**  | ~{tokens_estimados:,} |",
        ]

        if git.get('branch'):
            lineas.append(f"| **Branch**       | `{git['branch']}` |")
        if git.get('commit_hash'):
            lineas.append(f"| **Last commit**  | `{git['commit_hash']}` — {git['commit_msg']} |")
        if git.get('commit_date'):
            lineas.append(f"| **Commit date**  | {git['commit_date']} |")

        return '\n'.join(lineas) + '\n'

    def _asegurar_md(self, nombre: str) -> str:
        """Devuelve el nombre con extensión .md si no tiene extensión."""
        nombre = nombre.strip()
        if not nombre:
            nombre = "git_ingest_output.md"
        if not os.path.splitext(nombre)[1]:
            nombre += ".md"
        return nombre

    def exportar(self):
        paths = self.obtener_seleccionados()
        if not paths:
            messagebox.showinfo("Sin selección", "No seleccionaste archivos o carpetas.")
            return

        nombre = simpledialog.askstring(
            "Nombre del archivo",
            "Ingresa el nombre del archivo a guardar (sin ruta):",
            initialvalue="git_ingest_output.md",
            parent=self.root
        )
        if nombre is None:
            return

        nombre = self._asegurar_md(nombre)

        carpeta_contexts = os.path.join(os.getcwd(), "contexts")
        os.makedirs(carpeta_contexts, exist_ok=True)

        salida = os.path.join(carpeta_contexts, nombre)

        with open(salida, 'w', encoding='utf-8') as f:
            # --- Summary ---
            f.write(self.generar_summary(paths))
            f.write("\n")

            # --- Estructura de directorios ---
            f.write("## Directory Structure\n\n")
            f.write("```\n")
            f.write(self.generar_estructura(self.ruta_base))
            f.write("```\n")

            # --- Contenido de archivos ---
            f.write("\n## Files Content\n")

            for path in paths:
                if os.path.isfile(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as archivo:
                            contenido = archivo.read()

                        rel_path = os.path.relpath(path, self.ruta_base)
                        ext = os.path.splitext(path)[1].lower()
                        lang = EXTENSION_LANG.get(ext, '')

                        f.write(f"\n### `{rel_path}`\n\n")
                        f.write(f"```{lang}\n")
                        f.write(contenido)
                        if not contenido.endswith('\n'):
                            f.write('\n')
                        f.write("```\n")

                    except Exception:
                        rel_path = os.path.relpath(path, self.ruta_base)
                        f.write(f"\n### `{rel_path}`\n\n")
                        f.write("> ⚠️ Error al leer este archivo.\n")

        messagebox.showinfo("Exportación completa", f"Archivo guardado en:\n{salida}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)

    root.update_idletasks()
    width, height = 900, 600
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.deiconify()
    root.lift()
    root.focus_force()

    root.mainloop()