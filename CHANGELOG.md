# Histórico de versões

## 1.0.1

Correções de geometria: o que aparece na tela agora é o que sai no PDF.

### Corrigido

- **Texto salvo subia quase uma linha.** No Canvas o texto é desenhado com
  `anchor="nw"` — o ponto clicado é o **topo** da caixa. Já o
  `page.insert_text` do PyMuPDF usa esse ponto como **linha de base**, onde
  as letras "pisam". Sem somar o ascent da fonte, o texto inteiro subia
  cerca de uma altura de fonte. Agora a linha de base é calculada como
  `topo + ascent`.
- **Tamanho da fonte divergia entre tela e PDF.** `("Helvetica", 12)` no Tk
  é medido em pontos *da tela*, que o Tk multiplica pelo DPI do monitor
  (12 pt viravam 16 px a 96 dpi, e 24 px num monitor com escala de 150%).
  A página é renderizada a 72 dpi, onde 1 pt equivale a 1 px. Agora a fonte
  é criada com tamanho negativo (pixels), então a tela acompanha o PDF em
  qualquer DPI.
- **Objetos escorregavam em relação à página ao dar zoom.** As posições
  ficavam guardadas em pixels de tela, então mudar o zoom movia os objetos
  em relação ao conteúdo da página, e o PDF salvo dependia do zoom em que a
  página estava no momento de salvar. Posições e tamanhos passaram a ser
  guardados sempre em **pontos do PDF** (72 dpi); a conversão para a tela é
  só uma multiplicação pelo zoom.
- **Imagens saíam com o tamanho errado fora do zoom 1.0.** A tela usava
  `render_w * zoom` e o salvamento `render_w / zoom`: no zoom 2x a imagem
  ia para o PDF com metade do tamanho que aparecia na tela.
- **Imagem esticada voltava à proporção original ao salvar.** As alças
  permitem redimensionar livremente, mas o `insert_image` reimpunha a
  proporção da imagem (`keep_proportion=True` é o padrão) e a encolhia
  dentro do retângulo. Uma imagem de 400x200 esticada para 300x200 pt na
  tela era salva com 300x150.
- **Zoom sem limite superior.** `Ctrl + Scroll` subia o zoom
  indefinidamente, e o `get_pixmap` chegava a alocar imagens enormes,
  travando o app. O zoom agora vai de 0.25x a 8x.

### Adicionado

- `tests/test_geometry.py`: 64 verificações de posição e tamanho do texto e
  das imagens no PDF salvo, em cinco níveis de zoom, incluindo arrastar e
  redimensionar com zoom diferente de 1.0. Roda sem interação.
- `--version` e `--selftest` no executável, para conferir um build do
  PyInstaller sem abrir a janela: o `--selftest` cria um PDF, insere um
  texto e uma imagem pelo mesmo caminho do botão Salvar e confere a
  geometria do resultado.
- Versão no título da janela.

## 1.0.0

Versão inicial do editor visual: inserção de texto e imagens, objetos
arrastáveis, zoom, pan, undo/redo, mesclagem e extração de páginas,
exportação como imagem e salvamento com sobrescrita do arquivo original.
