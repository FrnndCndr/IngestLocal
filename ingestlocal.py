import tkinter as tk
from app.ui import App


def main() -> None:
    root = tk.Tk()
    App(root)

    root.update_idletasks()
    width, height = 900, 600
    x = (root.winfo_screenwidth()  // 2) - (width  // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    root.deiconify()
    root.lift()
    root.focus_force()
    root.mainloop()


if __name__ == '__main__':
    main()