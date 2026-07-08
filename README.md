# pdf-editor

Utilitario para edicao basica de PDFs via linha de comando usando PyMuPDF.

## Funcionalidades

- Adicionar texto como marca d'agua em qualquer pagina
- Rotacionar paginas individualmente (0/90/180/270 graus)

## Instalacao

```bash
pip install -r requirements.txt
```

## Uso

### Adicionar marca d'agua

```bash
python pdf_editor.py watermark entrada.pdf saida.pdf "RASCUNHO" --page 0 --x 200 --y 300 --size 48 --opacity 0.2
```

### Rotacionar pagina

```bash
python pdf_editor.py rotate entrada.pdf saida.pdf 90 --page 0
```

## Commits de setup do repositorio

```bash
git init
git add .
git commit -m "feat: initial commit with pdf basic manipulation"
git branch -M main
git remote add origin git@github.com:seu-usuario/pdf-editor.git
git push -u origin main
```
