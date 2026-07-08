import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import fitz
from PIL import Image, ImageTk


class VisualPDFEditor:
    def __init__(self, master):
        self.master = master
        master.title("Visual PDF Editor")
        master.geometry("900x700")

        self.pdf_document = None
        self.current_page = 0
        self.page_image = None
        self.tk_image = None

        self.render_zoom = 2.0
        self.display_scale = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0

        self._build_ui()

    def _build_ui(self):
        toolbar = tk.Frame(self.master)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        btn_open = tk.Button(toolbar, text="Abrir PDF", command=self.open_pdf)
        btn_open.pack(side=tk.LEFT, padx=2)

        btn_save = tk.Button(toolbar, text="Salvar PDF", command=self.save_pdf)
        btn_save.pack(side=tk.LEFT, padx=2)

        self.canvas = tk.Canvas(self.master, bg="gray")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        if self.pdf_document:
            self.pdf_document.close()

        self.pdf_document = fitz.open(path)
        self.current_page = 0
        self.render_page()

    def render_page(self):
        if not self.pdf_document:
            return

        page = self.pdf_document[self.current_page]
        mat = fitz.Matrix(self.render_zoom, self.render_zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.canvas.update_idletasks()
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)

        img_w, img_h = img.size
        scale_x = canvas_w / img_w
        scale_y = canvas_h / img_h
        self.display_scale = min(scale_x, scale_y)

        new_w = int(img_w * self.display_scale)
        new_h = int(img_h * self.display_scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        self.image_offset_x = (canvas_w - new_w) // 2
        self.image_offset_y = (canvas_h - new_h) // 2

        self.page_image = img
        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(
            self.image_offset_x, self.image_offset_y,
            anchor=tk.NW, image=self.tk_image
        )

    def on_canvas_click(self, event):
        if not self.pdf_document:
            return

        canvas_x = event.x - self.image_offset_x
        canvas_y = event.y - self.image_offset_y

        pdf_x = canvas_x / (self.render_zoom * self.display_scale)
        pdf_y = canvas_y / (self.render_zoom * self.display_scale)

        pdf_x = max(0, pdf_x)
        pdf_y = max(0, pdf_y)

        text = simpledialog.askstring(
            "Inserir Texto",
            f"Texto para posicao ({pdf_x:.0f}, {pdf_y:.0f}):",
            parent=self.master
        )

        if not text:
            return

        page = self.pdf_document[self.current_page]
        point = fitz.Point(pdf_x, pdf_y)
        page.insert_text(point, text, fontsize=12, color=(0, 0, 0))

        self.render_page()

    def save_pdf(self):
        if not self.pdf_document:
            return

        path = filedialog.asksaveasfilename(
            title="Salvar PDF",
            defaultextension=".pdf",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        self.pdf_document.save(path, garbage=4, deflate=True)
        messagebox.showinfo("Sucesso", f"PDF salvo em:\n{path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = VisualPDFEditor(root)
    root.mainloop()
