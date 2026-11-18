"""Testes de geometria do editor: posicao e tamanho dos objetos no PDF salvo.

Roda sem interacao: cria a janela escondida, monta as acoes direto (sem os
dialogos) e confere o PDF gerado com o PyMuPDF.

    python tests/test_geometry.py

Cobre os bugs corrigidos na 1.0.1:
  - objetos escorregavam em relacao a pagina ao mudar o zoom;
  - imagens salvavam com tamanho errado fora do zoom 1.0;
  - texto salvo subia quase uma linha (anchor nw x linha de base).
"""

import os
import sys
import tempfile
import tkinter as tk

import fitz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_gui_editor import VisualPDFEditor, __version__  # noqa: E402

PAGE_W, PAGE_H = 595, 842
TEXT_X, TEXT_Y = 100.0, 200.0
FONTSIZE = 24
IMG_X, IMG_Y = 120.0, 420.0
IMG_W, IMG_H = 200.0, 100.0
ZOOMS = [0.5, 1.0, 1.5, 2.0, 3.0]
TOL = 0.5

failures = []
checks = 0


def check(label, ok, detail=""):
    global checks
    checks += 1
    if ok:
        print("  ok   %s %s" % (label, detail))
    else:
        print("  FAIL %s %s" % (label, detail))
        failures.append(label)


def near(a, b, tol=TOL):
    return abs(a - b) <= tol


def make_fixtures(tmp):
    pdf_path = os.path.join(tmp, "base.pdf")
    doc = fitz.open()
    doc.new_page(width=PAGE_W, height=PAGE_H)
    doc.save(pdf_path)
    doc.close()

    img_path = os.path.join(tmp, "stamp.png")
    Image.new("RGB", (400, 200), (200, 30, 30)).save(img_path)
    return pdf_path, img_path


def build_app(pdf_path):
    root = tk.Tk()
    root.withdraw()
    app = VisualPDFEditor(root)
    app.filepath = pdf_path
    app.pdf_document = fitz.open(pdf_path)
    app.current_page = 0
    app._update_nav_state()
    return root, app


def seed_actions(app, img_path):
    app.actions = [
        {
            'type': 'text',
            'page': 0,
            'pdf_x': TEXT_X,
            'pdf_y': TEXT_Y,
            'text': "Hxg Teste",
            'fontsize': FONTSIZE,
            'color': (0.0, 0.0, 0.0),
        },
        {
            'type': 'image',
            'page': 0,
            'pdf_x': IMG_X,
            'pdf_y': IMG_Y,
            'img_width': 400,
            'img_height': 200,
            'pdf_w': IMG_W,
            'pdf_h': IMG_H,
            'filepath': img_path,
        },
    ]


def burn(app, out_path):
    doc = fitz.open(app.filepath)
    page = doc[0]
    for action in app.actions:
        app._burn_action_to_page(page, action)
    doc.save(out_path)
    doc.close()


def read_geometry(path):
    doc = fitz.open(path)
    page = doc[0]

    span = None
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for sp in line["spans"]:
                if span is None:
                    span = sp
    img_rects = [page.get_image_rects(info[0])[0] for info in page.get_images()]
    doc.close()
    return span, img_rects


def main():
    tmp = tempfile.mkdtemp(prefix="pdfed-test-")
    pdf_path, img_path = make_fixtures(tmp)
    root, app = build_app(pdf_path)

    print("Visual PDF Editor %s" % __version__)

    # 1) O PDF salvo nao pode depender do zoom em que a pagina estava.
    print("\n[1] geometria salva, invariante ao zoom")
    results = {}
    for zoom in ZOOMS:
        seed_actions(app, img_path)
        app.zoom_level = zoom
        app.render_page()
        out = os.path.join(tmp, "out-%s.pdf" % zoom)
        burn(app, out)
        span, img_rects = read_geometry(out)
        check("zoom %.2f: texto extraido" % zoom, span is not None)
        check("zoom %.2f: 1 imagem na pagina" % zoom,
              len(img_rects) == 1, "(%d)" % len(img_rects))
        if span is None or len(img_rects) != 1:
            continue
        results[zoom] = (span["origin"][0], span["origin"][1], img_rects[0])

        bx, by, rect = results[zoom]
        check("zoom %.2f: x do texto = %g" % (zoom, TEXT_X),
              near(bx, TEXT_X), "-> %.2f" % bx)
        check("zoom %.2f: imagem em (%g, %g)" % (zoom, IMG_X, IMG_Y),
              near(rect.x0, IMG_X) and near(rect.y0, IMG_Y),
              "-> (%.2f, %.2f)" % (rect.x0, rect.y0))
        check("zoom %.2f: imagem %gx%g pt" % (zoom, IMG_W, IMG_H),
              near(rect.width, IMG_W) and near(rect.height, IMG_H),
              "-> %.2fx%.2f" % (rect.width, rect.height))

    if len(results) == len(ZOOMS):
        ref = results[1.0]
        for zoom, got in results.items():
            check("zoom %.2f identico ao zoom 1.0" % zoom,
                  near(got[0], ref[0]) and near(got[1], ref[1])
                  and near(got[2].width, ref[2].width)
                  and near(got[2].height, ref[2].height))

    # 2) Linha de base: o texto fica ABAIXO do ponto clicado, a uma distancia
    #    igual ao ascent da fonte (foi o bug do texto "subindo").
    print("\n[2] linha de base do texto")
    ascent = app._ascent_pt(FONTSIZE)
    check("ascent/fontsize plausivel", 0.7 <= ascent / FONTSIZE <= 1.0,
          "-> %.0f/%d = %.3f" % (ascent, FONTSIZE, ascent / FONTSIZE))
    for zoom, (bx, by, _rect) in results.items():
        check("zoom %.2f: baseline = topo + ascent" % zoom,
              near(by, TEXT_Y + ascent), "-> %.2f (esperado %.2f)"
              % (by, TEXT_Y + ascent))
        check("zoom %.2f: texto abaixo do clique" % zoom,
              TEXT_Y < by <= TEXT_Y + FONTSIZE, "-> %.2f" % by)

    # 3) Na tela, os objetos ficam colados na pagina em qualquer zoom.
    print("\n[3] objetos acompanham a pagina na tela")
    seed_actions(app, img_path)
    for zoom in ZOOMS:
        app.zoom_level = zoom
        app.render_page()
        text_action, img_action = app.actions
        tx, ty = app.canvas.coords(text_action['canvas_id'])
        ix, iy = app.canvas.coords(img_action['canvas_id'])
        check("zoom %.2f: texto no canvas" % zoom,
              near(tx, TEXT_X * zoom) and near(ty, TEXT_Y * zoom),
              "-> (%.1f, %.1f)" % (tx, ty))
        check("zoom %.2f: imagem no canvas" % zoom,
              near(ix, IMG_X * zoom) and near(iy, IMG_Y * zoom),
              "-> (%.1f, %.1f)" % (ix, iy))
        bbox = app.canvas.bbox(img_action['canvas_id'])
        check("zoom %.2f: imagem escalada na tela" % zoom,
              near(bbox[2] - bbox[0], IMG_W * zoom, 1.5)
              and near(bbox[3] - bbox[1], IMG_H * zoom, 1.5),
              "-> %dx%d" % (bbox[2] - bbox[0], bbox[3] - bbox[1]))

    # 4) Arrastar com zoom != 1 grava a posicao certa em pontos do PDF.
    print("\n[4] arrastar objeto com zoom != 1.0")
    app.zoom_level = 2.0
    app.render_page()
    text_action = app.actions[0]
    cid = text_action['canvas_id']
    app.canvas.move(cid, 40, 60)  # 40x60 px de tela = 20x30 pt do PDF
    app._drag_data = {'item': cid, 'last_x': 0, 'last_y': 0}
    app.on_canvas_release(None)
    check("pdf_x apos arrastar", near(text_action['pdf_x'], TEXT_X + 20),
          "-> %.2f" % text_action['pdf_x'])
    check("pdf_y apos arrastar", near(text_action['pdf_y'], TEXT_Y + 30),
          "-> %.2f" % text_action['pdf_y'])

    out = os.path.join(tmp, "out-drag.pdf")
    burn(app, out)
    span, _ = read_geometry(out)
    check("posicao salva apos arrastar",
          span is not None and near(span["origin"][0], TEXT_X + 20)
          and near(span["origin"][1], TEXT_Y + 30 + ascent),
          "-> (%.2f, %.2f)" % (span["origin"][0], span["origin"][1]))

    # 5) Redimensionar imagem com zoom != 1 grava o tamanho certo.
    print("\n[5] redimensionar imagem com zoom != 1.0")
    seed_actions(app, img_path)
    app.zoom_level = 2.0
    app.render_page()
    img_action = app.actions[1]
    app._start_resize(img_action['canvas_id'], 'se', None)

    class _Ev(object):
        pass

    ev = _Ev()
    # Alca 'se' arrastada para 300x200 pt -> 600x400 px de tela.
    ev.x = (IMG_X + 300) * 2.0
    ev.y = (IMG_Y + 200) * 2.0
    app._do_resize(ev)
    app._resize_data = None
    check("pdf_w apos resize", near(img_action['pdf_w'], 300),
          "-> %.2f" % img_action['pdf_w'])
    check("pdf_h apos resize", near(img_action['pdf_h'], 200),
          "-> %.2f" % img_action['pdf_h'])

    out = os.path.join(tmp, "out-resize.pdf")
    burn(app, out)
    _, img_rects = read_geometry(out)
    check("tamanho salvo apos resize",
          len(img_rects) == 1 and near(img_rects[0].width, 300)
          and near(img_rects[0].height, 200),
          "-> %.2fx%.2f" % (img_rects[0].width, img_rects[0].height)
          if img_rects else "(sem imagem)")

    # 6) Limites do zoom.
    print("\n[6] limites do zoom")
    app.zoom_level = app.ZOOM_MAX
    app.zoom_in()
    check("zoom nao passa de %g" % app.ZOOM_MAX,
          app.zoom_level == app.ZOOM_MAX, "-> %g" % app.zoom_level)
    app.zoom_level = app.ZOOM_MIN
    app.zoom_out()
    check("zoom nao cai abaixo de %g" % app.ZOOM_MIN,
          app.zoom_level == app.ZOOM_MIN, "-> %g" % app.zoom_level)

    app.pdf_document.close()
    root.destroy()

    print("\n%d verificacoes, %d falhas" % (checks, len(failures)))
    if failures:
        for f in failures:
            print("  - %s" % f)
        return 1
    print("TODOS OS TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
