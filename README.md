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
git clone https://github.com/jothas2000/pdf-editor.git
cd pdf-editor
pip install -r requirements.txt
```

Se preferir não instalar o Python, baixe o executável pronto em
[Releases](https://github.com/jothas2000/pdf-editor/releases).

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


## Testes

Os testes de geometria conferem, sem abrir janela, se a posição e o tamanho
dos objetos no PDF salvo batem com o que aparece na tela — em vários níveis
de zoom.

```bash
python tests/test_geometry.py
```

## Compilação e Deploy (Release)

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconsole --onefile --name "PDF-Editor" --clean `
  --exclude-module numpy --exclude-module pandas --exclude-module scipy `
  --exclude-module matplotlib pdf_gui_editor.py
```

- O executável será gerado em `dist/PDF-Editor.exe` (~44 MB, Python e
  PyMuPDF embutidos).
- `python -m PyInstaller` (em vez de só `pyinstaller`) evita o erro de
  comando não encontrado quando o Scripts/ não está no PATH.
- Os `--exclude-module` cortam bibliotecas pesadas que o PyInstaller
  encontra instaladas no ambiente mas que o editor não usa. Sem eles o
  executável passa de 110 MB.
- Para conferir o build sem abrir a janela:

  ```powershell
  dist\PDF-Editor.exe --version    # confere se as libs foram empacotadas
  dist\PDF-Editor.exe --selftest   # insere texto e imagem num PDF e confere
  ```

  Os dois saem com código 0 quando está tudo certo.
- Feche o `.exe` antes de recompilar, senão o PyInstaller falha com o
  arquivo em uso.
- O Windows Defender às vezes marca executáveis `--onefile` como suspeitos.
  É falso positivo.
- Acesse o repositório no GitHub, vá em **Releases** > **Create a new release**
  e anexe o `.exe`.

## Histórico de versões

Ver [CHANGELOG.md](CHANGELOG.md).

## Autor

**Thales do Prado Menendez** — Ciência da Computação (UTFPR)