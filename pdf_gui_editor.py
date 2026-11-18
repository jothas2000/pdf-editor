import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, simpledialog, messagebox, colorchooser
import os
import sys
import fitz
from PIL import Image, ImageTk

__version__ = "1.0.1"


class VisualPDFEditor:
    def __init__(self, master):
        self.master = master
        master.title(f"Visual PDF Editor {__version__}")

        try:
            master.state('zoomed')
        except tk.TclError:
            try:
                master.attributes('-zoomed', True)
            except tk.TclError:
                w = master.winfo_screenwidth()
                h = master.winfo_screenheight()
                master.geometry(f"{w}x{h}+0+0")

        self.pdf_document = None
        self.filepath = None
        self.current_page = 0
        self.tk_image = None
        self.zoom_level = 1.0
        self.actions = []
        self.redo_stack = []
        self.pending_image = None
        self._drag_data = None
        self._resize_data = None
        self._selection = None
        self._floating_images = {}

        self._build_ui()

        master.bind("<Control-z>", self.undo_action)
        master.bind("<Control-Z>", self.undo_action)
        master.bind("<Control-y>", self.redo_action)
        master.bind("<Control-Y>", self.redo_action)
        master.bind("<Control-s>", self.save_pdf)
        master.bind("<Control-S>", self.save_pdf)
        master.bind("<Control-o>", self.open_pdf)
        master.bind("<Control-O>", self.open_pdf)
        master.bind("<Control-plus>", self.zoom_in)
        master.bind("<Control-equal>", self.zoom_in)
        master.bind("<Control-minus>", self.zoom_out)
        master.bind("<Escape>", self.cancel_action)

    @staticmethod
    def _rgb_to_hex(color):
        return "#{:02x}{:02x}{:02x}".format(
            int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
        )

    def _font_spec(self, fontsize):
        # Tamanho NEGATIVO = pixels no Tk (positivo seria pontos da tela, que o
        # Tk multiplica pelo DPI do monitor: 12 pt viram 16 px a 96 dpi).
        # A pagina e renderizada a 72 dpi * zoom, entao 1 pt do PDF = zoom px.
        return ("Helvetica", -max(1, round(fontsize * self.zoom_level)))

    # Posicoes e tamanhos dos objetos sao guardados SEMPRE em pontos do
    # PDF (72 dpi). O canvas desenha a pagina a 72 dpi * zoom, entao a
    # conversao entre os dois espacos e so uma multiplicacao pelo zoom.
    # Guardar em pixels de tela faria os objetos escorregarem em relacao
    # ao conteudo da pagina a cada mudanca de zoom.
    def _to_canvas(self, pdf_value):
        return pdf_value * self.zoom_level

    def _to_pdf(self, canvas_value):
        return canvas_value / self.zoom_level

    def _ascent_pt(self, fontsize):
        # Altura da linha de base ao topo das letras, em pontos do PDF.
        # Medida no tamanho SEM zoom: o PDF salvo usa o fontsize real, e
        # nao o arredondamento em pixels que aparece na tela.
        return tkfont.Font(
            font=("Helvetica", -max(1, round(fontsize)))
        ).metrics("ascent")

    def _build_ui(self):
        toolbar = tk.Frame(self.master)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        btn_open = tk.Button(toolbar, text="Abrir PDF", command=self.open_pdf)
        btn_open.pack(side=tk.LEFT, padx=2)

        btn_save = tk.Button(toolbar, text="Salvar PDF", command=self.save_pdf)
        btn_save.pack(side=tk.LEFT, padx=2)

        tk.Label(toolbar, text="  |  ").pack(side=tk.LEFT)

        btn_zoom_in = tk.Button(toolbar, text="Zoom +", command=self.zoom_in)
        btn_zoom_in.pack(side=tk.LEFT, padx=2)

        btn_zoom_out = tk.Button(toolbar, text="Zoom -", command=self.zoom_out)
        btn_zoom_out.pack(side=tk.LEFT, padx=2)

        tk.Label(toolbar, text="  |  ").pack(side=tk.LEFT)

        btn_image = tk.Button(toolbar, text="Inserir Imagem",
                              command=self.insert_image_mode)
        btn_image.pack(side=tk.LEFT, padx=2)

        btn_undo = tk.Button(toolbar, text="Desfazer", command=self.undo_action)
        btn_undo.pack(side=tk.LEFT, padx=2)

        btn_redo = tk.Button(toolbar, text="Refazer", command=self.redo_action)
        btn_redo.pack(side=tk.LEFT, padx=2)

        tk.Label(toolbar, text="  |  ").pack(side=tk.LEFT)

        btn_merge = tk.Button(toolbar, text="Mesclar PDF", command=self.merge_pdf)
        btn_merge.pack(side=tk.LEFT, padx=2)

        btn_extract = tk.Button(toolbar, text="Extrair Pagina",
                                command=self.extract_page)
        btn_extract.pack(side=tk.LEFT, padx=2)

        btn_export = tk.Button(toolbar, text="Exportar Imagem",
                               command=self.export_image)
        btn_export.pack(side=tk.LEFT, padx=2)

        btn_clear = tk.Button(toolbar, text="Limpar Alteracoes",
                              command=self.clear_changes)
        btn_clear.pack(side=tk.LEFT, padx=2)

        nav_frame = tk.Frame(self.master)
        nav_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 4))

        self.btn_prev = tk.Button(
            nav_frame, text="Pagina Anterior",
            command=self.prev_page, state=tk.DISABLED
        )
        self.btn_prev.pack(side=tk.LEFT, padx=2)

        self.page_label = tk.Label(nav_frame, text="Nenhum PDF aberto")
        self.page_label.pack(side=tk.LEFT, padx=12)

        self.btn_next = tk.Button(
            nav_frame, text="Proxima Pagina",
            command=self.next_page, state=tk.DISABLED
        )
        self.btn_next.pack(side=tk.LEFT, padx=2)

        canvas_frame = tk.Frame(self.master)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            canvas_frame, bg="gray",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scroll.config(command=self.canvas.yview)
        h_scroll.config(command=self.canvas.xview)

        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<Button-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        self.canvas.bind("<MouseWheel>", self.mouse_wheel_scroll)
        self.canvas.bind("<Button-4>", self.mouse_wheel_scroll)
        self.canvas.bind("<Button-5>", self.mouse_wheel_scroll)
        self.canvas.bind("<Control-MouseWheel>", self.mouse_wheel_zoom)
        self.canvas.bind("<Control-Button-4>", self.mouse_wheel_zoom)
        self.canvas.bind("<Control-Button-5>", self.mouse_wheel_zoom)

    # ─── Zoom ─────────────────────────────────────────────────────

    # Limites do zoom: acima de 8x o get_pixmap aloca uma imagem enorme
    # e o app pode travar ou estourar a memoria.
    ZOOM_MIN = 0.25
    ZOOM_MAX = 8.0
    ZOOM_STEP = 0.25

    def _set_zoom(self, value):
        new_zoom = min(self.ZOOM_MAX, max(self.ZOOM_MIN, value))
        if new_zoom == self.zoom_level:
            return
        self.zoom_level = new_zoom
        self.render_page()

    def zoom_in(self, event=None):
        self._set_zoom(self.zoom_level + self.ZOOM_STEP)

    def zoom_out(self, event=None):
        self._set_zoom(self.zoom_level - self.ZOOM_STEP)

    def mouse_wheel_zoom(self, event):
        if event.delta:
            zoom_in = event.delta > 0
        else:
            zoom_in = event.num == 4

        step = self.ZOOM_STEP if zoom_in else -self.ZOOM_STEP
        self._set_zoom(self.zoom_level + step)

    # ─── Scroll ───────────────────────────────────────────────────

    def mouse_wheel_scroll(self, event):
        if event.delta:
            delta = 1 if event.delta > 0 else -1
            self.canvas.yview_scroll(-delta * 3, "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(3, "units")

    # ─── Pan ──────────────────────────────────────────────────────

    def pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    # ─── Cancelamento ─────────────────────────────────────────────

    def cancel_action(self, event=None):
        if self.pending_image:
            self.pending_image = None
            self.canvas.config(cursor="")

    # ─── Navegacao ────────────────────────────────────────────────

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self._update_nav_state()

    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.render_page()
            self._update_nav_state()

    def _update_nav_state(self):
        if not self.pdf_document:
            self.btn_prev.config(state=tk.DISABLED)
            self.btn_next.config(state=tk.DISABLED)
            self.page_label.config(text="Nenhum PDF aberto")
            return

        total = len(self.pdf_document)
        self.page_label.config(text=f"Pagina {self.current_page + 1} de {total}")

        self.btn_prev.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if self.current_page < total - 1 else tk.DISABLED)

    # ─── PDF ──────────────────────────────────────────────────────

    def open_pdf(self, event=None):
        path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        if self.pdf_document:
            self.pdf_document.close()

        self.filepath = path
        self.pdf_document = fitz.open(path)
        self.current_page = 0
        self.zoom_level = 1.0
        self.actions = []
        self.redo_stack = []
        self.pending_image = None
        self._drag_data = None
        self._resize_data = None
        self._selection = None
        self._floating_images = {}
        self.canvas.config(cursor="")
        self._update_nav_state()
        self.render_page()

    # ─── Render ───────────────────────────────────────────────────

    def render_page(self):
        if not self.pdf_document:
            return

        self._drag_data = None
        self._resize_data = None
        self._selection = None

        page = self.pdf_document[self.current_page]
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self._floating_images = {}
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        for action in self.actions:
            if action.get('page') != self.current_page:
                continue

            if action['type'] == 'text':
                cid = self.canvas.create_text(
                    self._to_canvas(action['pdf_x']),
                    self._to_canvas(action['pdf_y']),
                    text=action['text'],
                    font=self._font_spec(action['fontsize']),
                    fill=self._rgb_to_hex(action['color']),
                    anchor="nw",
                    tags="floating"
                )
                action['canvas_id'] = cid

            elif action['type'] == 'image':
                self._create_floating_image(action)

    def _create_floating_image(self, action):
        disp_w = max(1, round(self._to_canvas(action['pdf_w'])))
        disp_h = max(1, round(self._to_canvas(action['pdf_h'])))
        img_obj = Image.open(action['filepath'])
        img_obj = img_obj.resize((disp_w, disp_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_obj)

        cid = self.canvas.create_image(
            self._to_canvas(action['pdf_x']),
            self._to_canvas(action['pdf_y']),
            image=tk_img, anchor="nw", tags="floating"
        )
        self._floating_images[cid] = tk_img
        action['canvas_id'] = cid

    # ─── Selecao ─────────────────────────────────────────────────

    def _clear_selection(self):
        if not self._selection:
            return
        self.canvas.delete(self._selection['rect_id'])
        for h in self._selection['handles'].values():
            self.canvas.delete(h)
        self._selection = None

    def _select_object(self, item_id):
        self._clear_selection()

        bbox = self.canvas.bbox(item_id)
        if not bbox:
            return

        x1, y1, x2, y2 = bbox
        hs = 6

        rect_id = self.canvas.create_rectangle(
            x1 - 2, y1 - 2, x2 + 2, y2 + 2,
            outline="blue", dash=(3, 3), tags="selection"
        )

        handles = {}
        for pos, (hx, hy) in {
            'nw': (x1 - 2, y1 - 2),
            'ne': (x2 - 2, y1 - 2),
            'sw': (x1 - 2, y2 - 2),
            'se': (x2 - 2, y2 - 2)
        }.items():
            h = self.canvas.create_rectangle(
                hx, hy, hx + hs, hy + hs,
                fill="white", outline="blue",
                tags=("handle", f"handle_{pos}")
            )
            handles[pos] = h

        self._selection = {
            'item_id': item_id,
            'rect_id': rect_id,
            'handles': handles
        }

    # ─── Criacao de objetos (clique no fundo) ────────────────────

    def _create_object(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x = self._to_pdf(canvas_x)
        pdf_y = self._to_pdf(canvas_y)

        if self.pending_image:
            img_pil = Image.open(self.pending_image)
            orig_w, orig_h = img_pil.size

            # Tamanho inicial em pontos do PDF: 1 px da imagem vira 1 pt,
            # limitado a 400 pt no maior lado.
            max_init = 400
            if orig_w > max_init or orig_h > max_init:
                ratio = min(max_init / orig_w, max_init / orig_h)
                pdf_w = orig_w * ratio
                pdf_h = orig_h * ratio
            else:
                pdf_w = float(orig_w)
                pdf_h = float(orig_h)

            disp_w = max(1, round(self._to_canvas(pdf_w)))
            disp_h = max(1, round(self._to_canvas(pdf_h)))
            img_pil = img_pil.resize((disp_w, disp_h), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_pil)

            cid = self.canvas.create_image(
                canvas_x, canvas_y, image=tk_img,
                anchor="nw", tags="floating"
            )
            self._floating_images[cid] = tk_img

            self.redo_stack.clear()
            self.actions.append({
                'type': 'image',
                'page': self.current_page,
                'pdf_x': pdf_x,
                'pdf_y': pdf_y,
                'img_width': orig_w,
                'img_height': orig_h,
                'pdf_w': pdf_w,
                'pdf_h': pdf_h,
                'filepath': self.pending_image,
                'canvas_id': cid
            })
            self.pending_image = None
            self.canvas.config(cursor="")
            return

        fontsize = simpledialog.askinteger(
            "Tamanho da Fonte",
            "Tamanho da fonte (padrao 12):",
            parent=self.master,
            initialvalue=12, minvalue=1, maxvalue=200
        )
        if fontsize is None:
            return

        color_rgb, _ = colorchooser.askcolor(
            title="Cor do Texto",
            parent=self.master,
            color=(0, 0, 0)
        )
        if color_rgb is None:
            return

        text = simpledialog.askstring(
            "Inserir Texto",
            f"Texto na posicao ({pdf_x:.0f}, {pdf_y:.0f}) da pagina:",
            parent=self.master
        )
        if not text:
            return

        color = tuple(c / 255.0 for c in color_rgb)

        cid = self.canvas.create_text(
            canvas_x, canvas_y,
            text=text,
            font=self._font_spec(fontsize),
            fill=self._rgb_to_hex(color),
            anchor="nw",
            tags="floating"
        )

        self.redo_stack.clear()
        self.actions.append({
            'type': 'text',
            'page': self.current_page,
            'pdf_x': pdf_x,
            'pdf_y': pdf_y,
            'text': text,
            'fontsize': fontsize,
            'color': color,
            'canvas_id': cid
        })

    def _update_floating_image_display(self, action):
        canvas_id = action['canvas_id']
        disp_w = max(1, round(self._to_canvas(action['pdf_w'])))
        disp_h = max(1, round(self._to_canvas(action['pdf_h'])))
        img_obj = Image.open(action['filepath'])
        img_obj = img_obj.resize((disp_w, disp_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_obj)

        self.canvas.itemconfig(canvas_id, image=tk_img)
        self._floating_images[canvas_id] = tk_img

    # ─── Redimensionamento de imagem ─────────────────────────────

    def _start_resize(self, item_id, handle_pos, event):
        for action in self.actions:
            if action.get('canvas_id') == item_id and action['type'] == 'image':
                self._resize_data = {
                    'item_id': item_id,
                    'handle': handle_pos,
                    'start_x': action['pdf_x'],
                    'start_y': action['pdf_y'],
                    'start_w': action['pdf_w'],
                    'start_h': action['pdf_h'],
                    'aspect': action['img_width'] / action['img_height']
                }
                break

    def _do_resize(self, event):
        data = self._resize_data
        # O estado inicial e o resultado ficam em pontos do PDF; so o
        # ponteiro do mouse chega em pixels de tela.
        cx = self._to_pdf(self.canvas.canvasx(event.x))
        cy = self._to_pdf(self.canvas.canvasy(event.y))

        x1, y1 = data['start_x'], data['start_y']
        x2 = x1 + data['start_w']
        y2 = y1 + data['start_h']

        if data['handle'] == 'se':
            nw = max(20, cx - x1)
            nh = max(20, cy - y1)
            nx, ny = x1, y1
        elif data['handle'] == 'ne':
            nw = max(20, cx - x1)
            nh = max(20, y2 - cy)
            nx, ny = x1, cy
        elif data['handle'] == 'sw':
            nw = max(20, x2 - cx)
            nh = max(20, cy - y1)
            nx, ny = cx, y1
        elif data['handle'] == 'nw':
            nw = max(20, x2 - cx)
            nh = max(20, y2 - cy)
            nx, ny = cx, cy
        else:
            return

        for action in self.actions:
            if action.get('canvas_id') == data['item_id'] and action['type'] == 'image':
                action['pdf_x'] = nx
                action['pdf_y'] = ny
                action['pdf_w'] = nw
                action['pdf_h'] = nh
                self.canvas.coords(
                    data['item_id'],
                    self._to_canvas(nx), self._to_canvas(ny)
                )
                self._update_floating_image_display(action)
                self._clear_selection()
                self._select_object(data['item_id'])
                break

    # ─── Clique / Arrasto / Solta ────────────────────────────────

    def on_canvas_press(self, event):
        if not self.pdf_document:
            return

        item = self.canvas.find_withtag("current")
        if not item:
            self._clear_selection()
            return

        item_id = item[0]
        tags = self.canvas.gettags(item_id)

        if "handle" in tags and self._selection:
            for t in tags:
                if t.startswith("handle_"):
                    self._start_resize(
                        self._selection['item_id'],
                        t.split("_")[1], event
                    )
                    return "break"
            return "break"

        if "floating" in tags:
            self._drag_data = {
                'item': item_id,
                'last_x': self.canvas.canvasx(event.x),
                'last_y': self.canvas.canvasy(event.y)
            }
            self._select_object(item_id)
            return "break"

        self._clear_selection()
        self._create_object(event)

    def on_canvas_drag(self, event):
        if self._resize_data:
            self._do_resize(event)
            return

        if not self._drag_data:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        dx = cx - self._drag_data['last_x']
        dy = cy - self._drag_data['last_y']
        self.canvas.move(self._drag_data['item'], dx, dy)
        self._drag_data['last_x'] = cx
        self._drag_data['last_y'] = cy

    def on_canvas_release(self, event):
        if self._resize_data:
            self._resize_data = None
            return

        if not self._drag_data:
            return

        item_id = self._drag_data['item']
        for action in self.actions:
            if action.get('canvas_id') == item_id:
                x, y = self.canvas.coords(item_id)
                action['pdf_x'] = self._to_pdf(x)
                action['pdf_y'] = self._to_pdf(y)
                break

        self._drag_data = None

    # ─── Edicao (duplo clique) ───────────────────────────────────

    def on_canvas_double_click(self, event):
        if not self.pdf_document:
            return

        item = self.canvas.find_withtag("current")
        if not item or "floating" not in self.canvas.gettags(item[0]):
            return

        item_id = item[0]
        for action in self.actions:
            if action.get('canvas_id') == item_id and action['type'] == 'text':
                self._edit_text_object(action)
                break

    def _edit_text_object(self, action):
        new_text = simpledialog.askstring(
            "Editar Texto", "Texto:",
            parent=self.master, initialvalue=action['text']
        )
        if new_text is not None:
            action['text'] = new_text
            self.canvas.itemconfig(action['canvas_id'], text=new_text)

        new_size = simpledialog.askinteger(
            "Tamanho da Fonte", "Tamanho:",
            parent=self.master, initialvalue=action['fontsize'],
            minvalue=1, maxvalue=200
        )
        if new_size is not None:
            action['fontsize'] = new_size
            self.canvas.itemconfig(
                action['canvas_id'],
                font=self._font_spec(new_size)
            )

        color_rgb, _ = colorchooser.askcolor(
            title="Cor do Texto", parent=self.master,
            color=self._rgb_to_hex(action['color'])
        )
        if color_rgb is not None:
            action['color'] = tuple(c / 255.0 for c in color_rgb)
            self.canvas.itemconfig(
                action['canvas_id'],
                fill=self._rgb_to_hex(action['color'])
            )

    def insert_image_mode(self):
        if not self.pdf_document:
            return
        path = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg"),
                ("Todos os arquivos", "*.*")
            ]
        )
        if not path:
            return
        self.pending_image = path
        self.canvas.config(cursor="crosshair")

    # ─── Undo / Redo ─────────────────────────────────────────────

    def _rebuild_document(self):
        if not self.filepath:
            return
        if self.pdf_document:
            self.pdf_document.close()
        self.pdf_document = fitz.open(self.filepath)
        for action in self.actions:
            if action['type'] == 'merge':
                src = fitz.open(action['filepath'])
                self.pdf_document.insert_pdf(src)
                src.close()

        if self.current_page >= len(self.pdf_document):
            self.current_page = len(self.pdf_document) - 1

    def undo_action(self, event=None):
        if not self.actions:
            return
        self.redo_stack.append(self.actions.pop())
        self._rebuild_document()
        self._update_nav_state()
        self.render_page()

    def redo_action(self, event=None):
        if not self.redo_stack:
            return
        self.actions.append(self.redo_stack.pop())
        self._rebuild_document()
        self._update_nav_state()
        self.render_page()

    # ─── Limpar Alteracoes ───────────────────────────────────────

    def clear_changes(self):
        if not self.pdf_document:
            return
        self.actions = [a for a in self.actions if a.get('page') != self.current_page]
        self.redo_stack.clear()
        self.render_page()

    # ─── Queima (burn) ───────────────────────────────────────────

    def _burn_action_to_page(self, page, action):
        # As acoes ja guardam pontos do PDF, entao o resultado salvo nao
        # depende do zoom em que a pagina estava na tela.
        pdf_x = action['pdf_x']
        pdf_y = action['pdf_y']

        if action['type'] == 'text':
            # No canvas o texto usa anchor="nw": (pdf_x, pdf_y) e o TOPO da
            # caixa do texto. Ja o insert_text posiciona pela LINHA DE BASE
            # (onde as letras "pisam"). Sem somar o ascent da fonte, o texto
            # salvo sobe quase uma linha inteira.
            baseline_y = pdf_y + self._ascent_pt(action['fontsize'])
            page.insert_text(
                fitz.Point(pdf_x, baseline_y),
                action['text'],
                fontsize=action['fontsize'],
                color=action['color']
            )
        elif action['type'] == 'image':
            rect = fitz.Rect(
                pdf_x, pdf_y,
                pdf_x + action['pdf_w'], pdf_y + action['pdf_h']
            )
            # keep_proportion=False: as alcas permitem esticar a imagem na
            # tela, e o padrao do insert_image (True) reimpunha a proporcao
            # original ao salvar, encolhendo a imagem dentro do retangulo.
            page.insert_image(
                rect, filename=action['filepath'], keep_proportion=False
            )

    # ─── Salvar ───────────────────────────────────────────────────

    def save_pdf(self, event=None):
        if not self.pdf_document:
            return

        path = filedialog.asksaveasfilename(
            title="Salvar PDF",
            defaultextension=".pdf",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        doc = fitz.open(self.filepath)
        for action in self.actions:
            if action['type'] == 'merge':
                src = fitz.open(action['filepath'])
                doc.insert_pdf(src)
                src.close()
            else:
                page = doc[action['page']]
                self._burn_action_to_page(page, action)

        if self.filepath and os.path.normpath(path) == os.path.normpath(self.filepath):
            tmp_path = path + ".tmp"
            try:
                doc.save(tmp_path, garbage=4, deflate=True)
            except Exception as e:
                doc.close()
                messagebox.showerror("Erro", f"Nao foi possivel salvar:\n{e}")
                return
            doc.close()
            self.pdf_document.close()
            os.replace(tmp_path, path)
            self.pdf_document = fitz.open(path)
            self.actions.clear()
            self.redo_stack.clear()
            self._floating_images = {}
            self.render_page()
        else:
            doc.save(path, garbage=4, deflate=True)
            doc.close()

        messagebox.showinfo("Sucesso", f"PDF salvo em:\n{path}")

    # ─── Exportar Imagem ─────────────────────────────────────────

    def export_image(self):
        if not self.pdf_document:
            return

        path = filedialog.asksaveasfilename(
            title="Exportar pagina como imagem",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Todos os arquivos", "*.*")
            ]
        )
        if not path:
            return

        doc = fitz.open(self.filepath)
        for action in self.actions:
            if action['type'] == 'merge':
                src = fitz.open(action['filepath'])
                doc.insert_pdf(src)
                src.close()

        page = doc[self.current_page]
        for action in self.actions:
            if action.get('page') == self.current_page:
                self._burn_action_to_page(page, action)

        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if path.lower().endswith(('.jpg', '.jpeg')):
            img.save(path, "JPEG", quality=95)
        else:
            img.save(path, "PNG")

        doc.close()
        messagebox.showinfo("Exportado", f"Pagina exportada como imagem:\n{path}")

    # ─── Mesclar ─────────────────────────────────────────────────

    def merge_pdf(self):
        if not self.pdf_document:
            return

        path = filedialog.askopenfilename(
            title="Selecionar PDF para mesclar",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        src = fitz.open(path)
        self.pdf_document.insert_pdf(src)
        src.close()

        self.redo_stack.clear()
        self.actions.append({
            'type': 'merge',
            'filepath': path
        })

        self._update_nav_state()
        messagebox.showinfo(
            "Mesclado",
            f"PDF mesclado. Total: {len(self.pdf_document)} paginas."
        )

    # ─── Extrair ─────────────────────────────────────────────────

    def extract_page(self):
        if not self.pdf_document:
            return

        path = filedialog.asksaveasfilename(
            title="Salvar pagina como",
            defaultextension=".pdf",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return

        doc = fitz.open()
        doc.insert_pdf(
            self.pdf_document,
            from_page=self.current_page,
            to_page=self.current_page
        )
        doc.save(path, garbage=4, deflate=True)
        doc.close()

        messagebox.showinfo(
            "Extraido",
            f"Pagina {self.current_page + 1} salva em:\n{path}"
        )


def _selftest():
    """Edita e salva um PDF de teste sem abrir a janela.

    Confere um build do PyInstaller de verdade: cria uma pagina, insere um
    texto e uma imagem pelo mesmo caminho do botao Salvar, le o resultado e
    confere a geometria. Retorna o codigo de saida do processo.
    """
    import tempfile

    tmp = tempfile.mkdtemp(prefix="pdfed-selftest-")
    pdf_path = os.path.join(tmp, "base.pdf")
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(pdf_path)
    doc.close()

    img_path = os.path.join(tmp, "stamp.png")
    Image.new("RGB", (400, 200), (200, 30, 30)).save(img_path)

    root = tk.Tk()
    root.withdraw()
    app = VisualPDFEditor(root)
    app.filepath = pdf_path
    app.pdf_document = fitz.open(pdf_path)
    app.current_page = 0
    app.zoom_level = 2.0
    app.actions = [
        {'type': 'text', 'page': 0, 'pdf_x': 100.0, 'pdf_y': 200.0,
         'text': "Selftest", 'fontsize': 24, 'color': (0.0, 0.0, 0.0)},
        {'type': 'image', 'page': 0, 'pdf_x': 120.0, 'pdf_y': 420.0,
         'img_width': 400, 'img_height': 200, 'pdf_w': 200.0, 'pdf_h': 100.0,
         'filepath': img_path},
    ]

    out_path = os.path.join(tmp, "out.pdf")
    doc = fitz.open(pdf_path)
    page = doc[0]
    for action in app.actions:
        app._burn_action_to_page(page, action)
    doc.save(out_path)
    doc.close()

    ascent = app._ascent_pt(24)
    app.pdf_document.close()
    root.destroy()

    doc = fitz.open(out_path)
    page = doc[0]
    spans = [sp for b in page.get_text("dict")["blocks"]
             for ln in b.get("lines", []) for sp in ln["spans"]]
    rects = [page.get_image_rects(info[0])[0] for info in page.get_images()]
    doc.close()

    problems = []
    if len(spans) != 1:
        problems.append("esperava 1 texto, achei %d" % len(spans))
    else:
        x, y = spans[0]["origin"]
        if abs(x - 100.0) > 0.5 or abs(y - (200.0 + ascent)) > 0.5:
            problems.append("texto em (%.2f, %.2f), esperado (100.00, %.2f)"
                            % (x, y, 200.0 + ascent))
    if len(rects) != 1:
        problems.append("esperava 1 imagem, achei %d" % len(rects))
    else:
        r = rects[0]
        if (abs(r.x0 - 120.0) > 0.5 or abs(r.y0 - 420.0) > 0.5
                or abs(r.width - 200.0) > 0.5 or abs(r.height - 100.0) > 0.5):
            problems.append("imagem em (%.2f, %.2f) %.2fx%.2f, esperado "
                            "(120.00, 420.00) 200.00x100.00"
                            % (r.x0, r.y0, r.width, r.height))

    if problems:
        print("SELFTEST FALHOU:")
        for p in problems:
            print("  - %s" % p)
        return 1

    print("Visual PDF Editor %s: selftest OK (texto e imagem salvos na "
          "posicao certa)" % __version__)
    return 0


if __name__ == "__main__":
    # Sai sem abrir a janela. Serve para checar um build do PyInstaller:
    # se o executavel responde aqui, o tkinter, o PyMuPDF e o Pillow foram
    # empacotados e carregaram direito.
    if "--version" in sys.argv[1:]:
        print(f"Visual PDF Editor {__version__}")
        sys.exit(0)

    if "--selftest" in sys.argv[1:]:
        sys.exit(_selftest())

    root = tk.Tk()
    app = VisualPDFEditor(root)
    root.mainloop()
