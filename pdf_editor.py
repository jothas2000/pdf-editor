import fitz  # PyMuPDF


def add_text_watermark(
    input_path: str,
    output_path: str,
    text: str,
    page_number: int = 0,
    x: float = 100,
    y: float = 100,
    font_size: float = 36,
    color: tuple[float, float, float] = (0.5, 0.5, 0.5),
    rotate: float = 0,
    opacity: float = 0.3,
) -> None:
    doc = fitz.open(input_path)
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Page {page_number} out of range (0-{len(doc) - 1})")

    page = doc[page_number]
    # Insere um bloco de texto livre para funcionar como marca d'agua,
    # sem depender de camadas de anotacao que alguns leitores ignoram.
    rect = fitz.Rect(x, y, x + 200, y + 50)
    page.insert_textbox(
        rect,
        text,
        fontsize=font_size,
        color=color,
        rotate=rotate,
        overlay=False,
        opacity=opacity,
    )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


def rotate_page(
    input_path: str,
    output_path: str,
    page_number: int = 0,
    angle: int = 90,
) -> None:
    valid_angles = {0, 90, 180, 270}
    if angle not in valid_angles:
        raise ValueError(f"Angle must be one of {valid_angles}")

    doc = fitz.open(input_path)
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Page {page_number} out of range (0-{len(doc) - 1})")

    page = doc[page_number]
    # Soma ao inves de setar para acumular multiplas chamadas
    # sem perder rotacoes anteriores.
    page.set_rotation(page.rotation + angle)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Utilitario para edicao basica de PDFs usando PyMuPDF."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- watermark ---
    wm = subparsers.add_parser("watermark", help="Adiciona texto como marca d'agua")
    wm.add_argument("input", help="Caminho do PDF de entrada")
    wm.add_argument("output", help="Caminho do PDF de saida")
    wm.add_argument("text", help="Texto da marca d'agua")
    wm.add_argument("--page", "-p", type=int, default=0, help="Numero da pagina (0-indexado)")
    wm.add_argument("--x", type=float, default=100, help="Coordenada X do texto")
    wm.add_argument("--y", type=float, default=100, help="Coordenada Y do texto")
    wm.add_argument("--size", type=float, default=36, help="Tamanho da fonte")
    wm.add_argument("--opacity", type=float, default=0.3, help="Opacidade (0-1)")

    # --- rotate ---
    rt = subparsers.add_parser("rotate", help="Rotaciona uma pagina")
    rt.add_argument("input", help="Caminho do PDF de entrada")
    rt.add_argument("output", help="Caminho do PDF de saida")
    rt.add_argument("angle", type=int, choices=[0, 90, 180, 270], help="Angulo de rotacao")
    rt.add_argument("--page", "-p", type=int, default=0, help="Numero da pagina (0-indexado)")

    args = parser.parse_args()

    if args.command == "watermark":
        add_text_watermark(
            args.input,
            args.output,
            args.text,
            page_number=args.page,
            x=args.x,
            y=args.y,
            font_size=args.size,
            opacity=args.opacity,
        )
        print(f"Watermark adicionado em {args.output}")
    elif args.command == "rotate":
        rotate_page(args.input, args.output, page_number=args.page, angle=args.angle)
        print(f"Pagina rotacionada salva em {args.output}")
