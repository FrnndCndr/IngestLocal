import customtkinter as ctk
from app.ui import App


def main() -> None:
    root = ctk.CTk()
    App(root)

    root.update_idletasks()
    w, h = 960, 620
    x = (root.winfo_screenwidth()  // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f'{w}x{h}+{x}+{y}')
    root.minsize(720, 480)
    root.deiconify()
    root.lift()
    root.focus_force()
    root.mainloop()


if __name__ == '__main__':
    main()