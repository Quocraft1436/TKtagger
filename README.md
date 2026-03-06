# TKtagger

A powerful image tagging tool built with PySide6, supporting WD14 Tagger and bulk tag management.

> **Note:** This project uses AI assistance for coding.

---

## Interface

![Main Interface](src/Screenshot_20260305_190358.png)

---

## Features

- **Bulk tag editing** — Add, remove, replace, or sort tags across multiple images at once
- **WD14 Tagger** — Automatic tagging via local model or external API
- **Undo / Redo** — Up to 100 steps with a full operation history window (`Edit → Operation history` or `🕐 History`)
- **Tag search** — Filter and find tags across your image set quickly
- **Quick tag interaction** — Click directly on a tag to delete or insert
- **Optimized image loading** — Reduced memory usage and faster display
- **Multi-language support** — Interface available in multiple languages (i18n)
- **Command-line argument** — Launch directly into a folder: `python main.py [path_folder]`

---

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python3 main.py

# Open directly into a specific folder
python3 main.py /path/to/folder
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all images |
| `Ctrl+I` | Invert selection |
| `Ctrl+D` | Deselect all |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

---

## Project Structure

```
tktagger/
├── main.py            # Entry point
├── main_window.py     # Main window
├── image_grid.py      # Image grid widget (ImageGrid, ImageCard)
├── tag_panel.py       # Right panel tag (TagPanel)
├── history_manager.py # Undo/Redo manager (HistoryManager)
├── history_window.py  # Operation history window
├── file_ops.py        # Read/write files (load/save tags)
├── Dialogs.py         # Dialogs (Sort, Replace, About)
└── README.md
```

---

## Roadmap

1. ✅ Basic tagger UI
2. ✅ Integrated WD14
3. ✅ Multiple language support
4. ⬜ System dictionary tags
5. ⬜ Redesigned UI
