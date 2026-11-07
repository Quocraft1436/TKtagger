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
- **WD14 Tagger** — Automatic tagging via a local model or an installed tool’s Python / models
- **Undo / Redo** — Up to 256 steps with a full operation history window (`Edit → Operation history` or `🕐 History`)
- **Tag search** — Filter and find tags across your image set quickly with JEI-style multi-token search
- **Quick tag interaction** — Click directly on a tag to delete or insert
- **Optimized image loading** — Reduced memory usage and faster display
- **Multi-language support** — English, Vietnamese, Simplified Chinese (ZH), Korean (KO), Japanese (JA/JP), and Russian (RU)
- **Command-line argument** — Launch directly into a folder: `python main.py [path_folder]`
- **Dictionary system** — Organize tags into named groups with virtual tag expansion
- **Resort by groups** — Reorder tags in `.txt` files according to dictionary group order, with ~~`BREAK`~~ `NewLine` ~~separator support for Kohya training~~ for visual look extenal editor

---

## Quick launch and packages

Linux: double-click `TKtagger.desktop` (generate with `python build/create_shortcut.py`)
or run `./launch.sh`. Windows: double-click `launch.cmd`. Use `--setup` once if
PySide6 is missing; the launcher installs it into a private `.venv`.

```bash
./build/build.sh                    # AppImage GUI on Linux
./build/build.sh --with-onnx        # Include local ONNX libraries
./build/build.sh --download-model   # Include ONNX + download/bundle WD14 model
```

On Windows use `build\build.cmd` with the same flags to build an EXE.
See [build instructions](build/README.md) for offline models, GPU options,
output locations and writable settings in packaged builds.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

For inference inside TKtagger's own venv, optionally install
`pip install -r requirements-local.txt`. The installed-tool mode only needs
PySide6 in TKtagger; numpy, Pillow and onnxruntime are reused from the tool.

## WD14: reuse an installed tool

Choose **Installed tool** instead of the former API mode, then:

1. Browse to the Kohya_ss or sd-scripts installation folder.
2. Select **Auto detect**, **Kohya_ss**, or **sd-scripts**, then click **Scan**.
3. Confirm the detected Python (`.venv`, `venv`, or `env`); you can browse to
   another Python executable if the venv has moved or uses a different layout.
4. Choose a detected ONNX model. Only pairs with `selected_tags.csv` are listed.
   You can also specify the ONNX and CSV files manually.

Kohya_ss maps models under `wd14_tagger_model/`; sd-scripts checks
`wd14_tagger_model/` and `models/`. Existing model files are read in place;
this mode does not download models, copy the venv, or start a Gradio server.
Tool type maps model locations; inference uses TKtagger's ONNX worker with the
selected tool's Python, rather than invoking its caption-writing scripts.
The selected tool, Python and model are remembered between runs.

Both modes keep results in RAM until **Save**, including results for unopened
subfolders. Undo/Redo records changes per folder. You may browse folders while
inference runs; opening another root folder and closing the application wait
until it finishes. With **Include subfolders** enabled, the current collection
scope starts at the dataset root shown in the folder tree.

A mounted/copied venv must still be runnable on this machine; broken interpreter
links or missing native/CUDA libraries require selecting a working Python.

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
│   ├── vi.json                     # Vietnamese
│   ├── zh.json                     # Simplified Chinese
│   ├── ko.json                     # Korean
│   ├── ja.json                     # Japanese (JP alias supported)
│   └── ru.json                     # Russian
│
├── libs/                           # Reusable UI components
│   └── draggable_list.py           # Draggable list widget with per-item deletion
│
├── tools/                          # Dataset processing tools
│   ├── waifu_tagger_window.py      # WD14 Tagger — local or installed tool
│   ├── tagger_logic.py             # ONNX inference (also used by the external worker)
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

## Automated testing and dataset backups

Run `python -m tests.run_ate` for safety tests plus real Qt rendering of
10,000 images in the virtual grid plus a smaller batch scenario, using
RAM-backed PNGs by default. Only viewport cards exist at once; thumbnails decode
on workers and use a bounded 64 MiB cache. Single-image edits store sparse
history deltas and update tag counts without rebuilding the grid. Folder metadata
loads in the background; the folder tree loads branches on expansion. Preview images and JSON reports live under `tests/artifacts/`.
Disk dataset generation is opt-in via `--disk-count`. See
[ATE instructions](tests/README.md) for thresholds, limitations and restoring
the automatic folder backups created before dataset saves and renames.

See [10,000-image sample](tests/performance_sample_10000.md) for measured results and limits.
