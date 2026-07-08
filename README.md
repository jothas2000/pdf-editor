# Visual PDF Editor

Ferramenta WYSIWYG leve construída em Python para edição visual de PDFs. Abra qualquer PDF, clique na posição desejada e insira textos ou imagens como objetos flutuantes — sem depender de softwares pesados ou pagos.

## Funcionalidades

- Inserção de textos com fonte, tamanho e cor customizáveis
- Inserção de imagens (assinaturas, carimbos) com redimensionamento visual por handles
- Objetos flutuantes arrastáveis livremente pelo Canvas
- Zoom com Ctrl + Scroll do mouse
- Pan (arrastar tela) com o botão do meio do mouse
- Scroll vertical com o mouse
- Undo / Redo ilimitados (Ctrl+Z / Ctrl+Y)
- Atalhos de teclado para todas as operações principais
- Mesclagem de PDFs (anexar páginas de outro arquivo)
- Extração de páginas para um novo PDF
- Exportação da página atual como PNG ou JPEG
- Salvamento com suporte a sobrescrita do arquivo original (sem lock)

## Instalação

```bash
git clone https://github.com/seu-usuario/visual-pdf-editor.git
cd visual-pdf-editor
pip install -r requirements.txt
```

## Como usar

```bash
python pdf_gui_editor.py
```

1. Clique em **Abrir PDF** e selecione o arquivo.
2. Para inserir texto: clique no fundo da página, escolha tamanho e cor, digite o texto.
3. Para inserir imagem: clique em **Inserir Imagem**, selecione o arquivo e clique na posição desejada.
4. Arraste objetos com o mouse para reposicioná-los.
5. Redimensione imagens arrastando as alças azuis nos cantos.
6. Clique duas vezes em um texto para editá-lo.
7. Clique em **Salvar PDF** ou use Ctrl+S para exportar.

## Atalhos

| Atalho          | Ação                     |
|-----------------|--------------------------|
| Ctrl + O        | Abrir PDF                |
| Ctrl + S        | Salvar PDF               |
| Ctrl + Z        | Desfazer                 |
| Ctrl + Y        | Refazer                  |
| Ctrl + Scroll   | Zoom In / Zoom Out       |
| Ctrl + + / -    | Zoom In / Zoom Out       |
| Esc             | Cancelar modo imagem     |
| Scroll          | Rolagem vertical         |
| Botão do meio   | Arrastar tela (Pan)      |


## Compilação e Deploy (Release)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile pdf_gui_editor.py
```

- O executável será gerado em `dist/pdf_gui_editor.exe`.
- Acesse o repositório no GitHub, vá em **Releases** > **Create a new release**.
- Anexe o arquivo `dist/pdf_gui_editor.exe` manualmente e publique a release.

## Autor

**Thales do Prado Menendez** — Ciência da Computação (UTFPR)