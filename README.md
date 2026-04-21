# PyReaderPDF

Leitor de PDF para desktop com interface Fluent Design, construído com Python, PySide6 e PyMuPDF.

## Funcionalidades

- **Biblioteca pessoal** — adicione PDFs à sua biblioteca com miniaturas geradas automaticamente
- **Histórico de recentes** — acesso rápido aos últimos arquivos abertos
- **Progresso automático** — reabre cada PDF na última página lida
- **Abas com arrastar e soltar** — reordene abas arrastando, abra múltiplos PDFs simultaneamente
- **Split View** — visualize dois PDFs lado a lado (via atalho ou arrastar aba)
- **Modos de visualização** — página única ou rolagem contínua
- **Anotações** — salve citações e notas por página em cada PDF
- **Busca na biblioteca** — filtre por nome ou caminho
- **Tema escuro** com Fluent Design via `qfluentwidgets`
- **HiDPI** — suporte a telas de alta resolução

## Requisitos

- Python 3.10+
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [PySide6](https://doc.qt.io/qtforpython/)
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) (`qfluentwidgets`)

## Instalação

```bash
git clone https://github.com/seu-usuario/pyreader-pdf.git
cd pyreader-pdf
pip install -r requirements.txt
python main.py
```

> O `requirements.txt` não inclui `qfluentwidgets`. Instale separadamente:
> ```bash
> pip install PyQt-Fluent-Widgets[Full]
> ```

## Atalhos de teclado

| Atalho | Ação |
|---|---|
| `Ctrl+O` | Abrir PDF |
| `Ctrl+W` | Fechar aba / sair do Split View |
| `Ctrl+D` | Duplicar aba atual |
| `Ctrl+→` | Split View com aba ativa à esquerda |
| `Ctrl+←` | Split View com aba ativa à direita |
| `Esc` | Fechar Split View |

## Arquivos de dados

O app salva os dados do usuário em arquivos JSON no diretório home:

| Arquivo/Pasta | Conteúdo |
|---|---|
| `~/.pyreaderpdf_library.json` | Lista da biblioteca com miniaturas |
| `~/.pyreaderpdf_config.json` | Configurações (zoom padrão, modo de visualização) |
| `~/.pyreaderpdf/progress.json` | Última página lida por PDF |
| `~/.pyreaderpdf_notes/` | Anotações por PDF (um arquivo JSON por livro) |

## Tecnologias

- **[PySide6](https://doc.qt.io/qtforpython/)** — framework de interface gráfica
- **[PyMuPDF](https://pymupdf.readthedocs.io/)** — renderização e extração de texto de PDFs
- **[PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)** — componentes Fluent Design
- **[Pillow](https://pillow.readthedocs.io/)** — geração de miniaturas
