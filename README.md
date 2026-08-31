# TKtagger

A powerful image tagging tool built with PySide6, supporting WD14 Tagger and bulk tag management.

> **Note:** This project uses AI assistance for coding.

---

## Interface

![Main Interface](src/Screenshot_20260831_112158.png)

English (README.md), Tiếng Việt (src/README_VN.md)

---

## Features

- **Bulk tag editing** — Add, remove, replace, or sort tags across multiple images at once
- **WD14 Tagger** — Automatic tagging via local model or external API
- **Undo / Redo** — Up to 256 steps with a full operation history window (`Edit → Operation history` or `🕐 History`)
- **Tag search** — Filter and find tags across your image set quickly with JEI-style multi-token search
- **Quick tag interaction** — Click directly on a tag to delete or insert
- **Optimized image loading** — Reduced memory usage and faster display
- **Multi-language support** — Interface available in multiple languages (i18n)
- **Command-line argument** — Launch directly into a folder: `python main.py [path_folder]`
- **Dictionary system** — Organize tags into named groups with virtual tag expansion
- **Resort by groups** — Reorder tags in `.txt` files according to dictionary group order, with ~~`BREAK`~~ `NewLine` ~~separator support for Kohya training~~ for visual look extenal editor

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
python3 main.py /path/to/folder_app
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
| `Ctrl+E` / `F5` | Remove duplicate tags |
| `Ctrl+R` / `F6` | Sort tags operations|
| `Ctrl+T` / `F8` | Open WD14 Tagger |
| `Ctrl+Shift+D` / `F9` | Open Dataset Calculator |

---

## Project Structure
```
TKtagger/
│
├── main.py                         # Entry point
├── main_window.py                  # MainWindow (QMainWindow) — core UI
├── settings_manager.py             # Singleton settings via ConfigParser (settings.ini)
├── settings.ini                    # User settings file (auto-generated)
│
├── tag_panel.py                    # Right-side panel: tag list organized by folder
├── image_grid.py                   # Image display grid and selection management
├── file_ops.py                     # Load/save images & tags, build folder tree
├── history_manager.py              # Undo/Redo stack manager
├── history_window.py               # UI panel displaying Action History
├── dialogs.py                      # AboutDialog and other small dialogs
├── i18n.py                         # Internationalization (tr(), set_language())
│
├── default_dictbook.json           # Default dictionary included with the app
├── requirements.txt                # Dependencies
│
├── lang/                           # Language files
│   ├── en.json                     # English
│   └── vi.json                     # Vietnamese
│
├── libs/                           # Reusable UI components
│   └── draggable_list.py           # Draggable list widget with per-item deletion
│
├── tools/                          # Dataset processing tools
│   ├── waifu_tagger_window.py      # WD14 Tagger — auto-tag images via ONNX / API
│   ├── tagger_logic.py             # Inference logic (local + API modes)
│   ├── calculator_dataset.py       # Dataset Calculator dialog
│   ├── dict_tags.py                # Dict Tags manager + VirtualTagEngine
│   ├── remove_duplicate_tags.py    # Remove duplicate tags in .txt files
│   ├── replace_tags.py             # Replace tags dialog (bulk edit)
│   └── resort_tag_window_operation.py  # Resort + Sort tags (merge from 2 old files)
│
└── src/                            # Assets
├── Qt_logo_2016.svg
└── Screenshot_*.png            # Preview images for README
```

---

## Changelog [1.5.0] - 2026-08-31

### Added
- New tool: Swap Underscore (`tools/underscore_swap.py`) — toggles between
underscores ("_") and spaces (" ") in tags; supports global application.
- Menubar > Settings: new settings window (`settings_dialog.py`) allowing:
- Selection of interface language (multi-language support, loaded from `lang/*.json`)
- Selection of tag file format upon loading: .txt / .cap / custom extension
- Setting the maximum history limit (`max_history` spinbox)
- Positioning options for batch tag addition: insert at the start or end
of the tag list (`add_tag_to_selected`).
- Select All / Invert Selection / Deselect All buttons for the main tag filter panel
(tag_panel.py).
- Preset dictionary: saves the path and structure of the most recently used
group dictionary to `preset_user.json` for quick reuse.
- Functionality to import new tags not currently in the dictionary (`ImportNewTagsDialog`
in dict_tags.py).

### Changed
- Improved image card rendering performance: replaced multiple individual QLabels
per tag with a custom-drawn widget, `TagRenderWidget` (using QPainter);
tags are displayed as rounded-corner labels and are clickable for editing.
- Comprehensive code refactoring (rewrote several modules: main_window, image_grid,
dict_tags, resort_tag_window_operation).

### Fixed
- Fixed tag reordering state synchronization issue: the interface (image cards,
tag panel) now refreshes before the "complete" notification dialog appears,
preventing the UI from lagging behind the notification.

**Note:** Please note that this information was summarized and written by AI. ## Roadmap

1. ✅ Basic tagger UI
2. ✅ Integrated WD14
3. ✅ Multi-language support
4. ✅ System dictionary tags
5. ✅ Redesigned UI

Once the roadmap is complete, subsequent updates will mostly be minor, focusing on maintenance and bug fixes.
