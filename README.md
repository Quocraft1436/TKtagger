#TKtagger - PySide6 Version

Application management tag for images based on the Danbooru standard, rewritten in PySide6 with an architecture module.

##Project Configuration

```
tktagger/
├── main.py # Entry Points
├── main_window.py # Main Window
├── image_grid.py # Image Grid Widget (ImageGrid, ImageCard)
├── tag_panel.py # Right Panel Tag (TagPanel)
├── history_manager.py # Undo/Redo Manager (HistoryManager)
├── history_window.py # Operation History Window
├── file_ops.py # Read/Write Files (Load/Save Tags)
├── Dialogs.py # Dialogs (Sort, Replace, About)
└── README.md

## Installation

bash
pip install PySide6 Pillow

## Running the application

bash
python main.py

## New features (compared to Tkinter)

### ✅ History window (Operation history)
- Open from the **Edit → Operation history** menu or the **🕐 History** button on the toolbar
- Displays a list of operations that can be Undo and Redo
- Undo/Redo buttons directly in the window
- Button to clear all history

### ✅ Ctrl+Z (Undo)
- Completes the last operation performed
- Supports up to 100 undo steps

### ✅ Ctrl+Y (Redo)
- Redoes the previously undone operation

### ✅ Operations tracked in history:

- Add tag Selected Image - Remove tag from selected image
- Add tags to individual images
- Remove duplicate tags
- Sort tags
- Delete tags in bulk
- Replace tags in bulk

## Disable Keys

| Key | Function |
|------|-------------|
| Ctrl+A | Select all images |
| Ctrl+I | Invert selection |
| Ctrl+D | Deselect all |
| Ctrl+S | Save |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+O | ​​Open folder |
| Ctrl+T | WD14 Tagger