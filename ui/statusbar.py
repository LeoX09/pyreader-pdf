import tkinter as tk


class Statusbar(tk.Label):
    """Barra de status na parte inferior da janela."""

    def __init__(self, parent):
        super().__init__(parent, text="Nenhum arquivo aberto",
                         bg="#2d2d2d", fg="#888", anchor=tk.W, padx=10)

    def update(self, current: int, total: int, zoom: float):
        self.config(text=f"Página {current} de {total}  |  Zoom: {int(zoom * 100)}%")

    def set_message(self, message: str):
        self.config(text=message)
