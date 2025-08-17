import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

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

        # --- NUEVOS BOTONES: Seleccionar/Deseleccionar todo ---
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
        # ------------------------------------------------------

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
        # Evitar cambiar estado si no se clickea sobre una fila
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
        nombre = texto[4:]  # quitar el "[ ] " o "[✔] "
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
            # Si quieres estado "indeterminado", podrías cambiar el texto aquí;
            # por simplicidad, lo dejamos marcado cuando hay mezcla.
            self.actualizar_checkbox(padre, True)
        else:
            self.actualizar_checkbox(padre, False)
        self.actualizar_padres(padre)

    def seleccionar_deseleccionar_todo(self, estado: bool):
        """Marca o desmarca todos los nodos del árbol."""
        for item in self.tree.get_children():
            self.actualizar_checkbox(item, estado)
            self.propagar_a_hijos(item, estado)
        # No es necesario actualizar padres porque todos quedan uniformes.

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

    def _asegurar_txt(self, nombre: str) -> str:
        """Devuelve el nombre con extensión .txt si no la tiene."""
        nombre = nombre.strip()
        if not nombre:
            nombre = "git_ingest_output.txt"
        if not os.path.splitext(nombre)[1]:
            nombre += ".txt"
        return nombre

    def exportar(self):
        paths = self.obtener_seleccionados()
        if not paths:
            messagebox.showinfo("Sin selección", "No seleccionaste archivos o carpetas.")
            return

        # Preguntar nombre del archivo
        nombre = simpledialog.askstring(
            "Nombre del archivo",
            "Ingresa el nombre del archivo a guardar (sin ruta):",
            initialvalue="git_ingest_output.txt",
            parent=self.root
        )
        if nombre is None:
            # Usuario canceló
            return

        nombre = self._asegurar_txt(nombre)

        # Crear carpeta contexts en el directorio de trabajo actual
        carpeta_contexts = os.path.join(os.getcwd(), "contexts")
        os.makedirs(carpeta_contexts, exist_ok=True)

        salida = os.path.join(carpeta_contexts, nombre)

        with open(salida, 'w', encoding='utf-8') as f:
            f.write("### Directory Structure:\n\n")
            f.write(self.generar_estructura(self.ruta_base))
            f.write("\n\n### Files Content:\n")
            for path in paths:
                if os.path.isfile(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as archivo:
                            contenido = archivo.read()
                        f.write(f"\n\n==== {os.path.relpath(path, self.ruta_base)} ====\n")
                        f.write(contenido)
                    except:
                        f.write(f"\n\n[Error al leer {path}]\n")

        messagebox.showinfo("Exportación completa", f"Archivo guardado en:\n{salida}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)

    # Mostrar ventana centrada
    root.update_idletasks()
    width, height = 900, 600
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.deiconify()
    root.lift()
    root.focus_force()

    root.mainloop()
