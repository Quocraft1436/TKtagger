# TKtagger Desktop tutorial

**English** · [Tiếng Việt](tutorial_vi.md)

[English README](README.md) · [Project structure — Tiếng Việt](Project_Structure.md)

This guide assumes you understand datasets, captions/tags and basic AI training concepts. Start the application with `launch.cmd` on Windows or `sh ./launch.sh` on Linux. See the README if you need to run `--setup` first.

## 1. Default keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open a dataset folder |
| `Ctrl+S` | Save changed captions |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+A` | Select all images |
| `Ctrl+D` | Deselect all images |
| `Ctrl+I` | Invert the image selection |
| `Ctrl+E` or `F5` | Remove duplicate tags |
| `Ctrl+R` or `F6` | Sort tags |
| `Ctrl+Shift+U` | Switch underscores and spaces |
| `Ctrl+T` or `F8` | Open WD14 Tagger |
| `Ctrl+Shift+D` or `F9` | Open Dataset Calculator |

Standard shortcuts such as Undo/Redo may differ by operating system; the menus show the assigned shortcuts. When a text field has focus, it may handle text-editing shortcuts itself.

Open **Settings → Keyboard shortcuts** to assign primary and alternative bindings, clear a binding or restore defaults. Dictionary and Help menu commands are excluded from shortcut customization.

## 2. Open a folder and explore the interface

1. Choose **File → Open folder** or press `Ctrl+O`.
2. Select the dataset root, then click a folder in the tree to view its images.
3. Check the caption extension in **Settings → General**: `.txt`, `.cap` or a custom extension. When changing it, follow the application's restart prompt.

Captions share the image's base filename, for example `image_001.png` and `image_001.txt`. Tags are separated by commas.

| Component | How to use it |
|---|---|
| Folder tree | Navigate between folders in the dataset. |
| Image grid | Click cards to select/deselect them; use Select all, Invert selection or Deselect all. |
| Tag panel | Search tags, select tag filters and open tag removal/replacement tools. |
| Bottom input bar | Enter tags to add to or remove from selected images. |
| Preview | Click a card's preview button, then use the preview dock to inspect and zoom the image. |
| History | Open from the Edit menu or the History button to inspect operations and use Undo/Redo. |

Selecting **images** in the grid and selecting **tags** in the tag panel are different scopes. Check the scope of each tool before applying it.

In **Settings → General**, choose **Classic** to set the column count manually or **Auto fit** to use the available width. Choose **Moderate**, **Taller** or **Full tag content** card height according to how much caption text you want to see.

## 3. Add tags with the input bar: Begin / Last

1. Select one or more images in the grid.
2. Enter tags, for example `blue_sky, outdoors`.
3. Choose **Begin** or **Last**, then click **Add tags**.

Starting with `landscape`, the result is:

```text
Begin: blue_sky, outdoors, landscape
Last:  landscape, blue_sky, outdoors
```

New tags keep the order you entered. Duplicates in the input and tags already present on an image are skipped; existing tags keep their positions. Images are deselected after a bulk operation, so select them again before the next operation.

To remove tags from selected images, enter them in the same input bar and click **Remove tags**. The input on an individual image card adds tags only to that image when you press Enter. In a card's tag area:

- **Right-click:** copy the tag into the shared input bar.
- **Middle-click:** request removal of that tag from the image.

Use Undo/Redo to review changes, then click **Save** when you want to write captions to disk.

## 4. Use batch tools

| Tool | Basic use and scope |
|---|---|
| Remove duplicate tags | Open from the Tool menu or press `F5`; processes the currently loaded images in the current folder. |
| Replace tags | Select tags in the tag panel, click Replace, enter replacement values and confirm; updates loaded images containing matching tags. |
| Sort tags | Open with `F6`, choose the rules/dictionary group order in the tool window and apply. |
| Underscores/spaces | Choose a conversion direction, such as `blue_sky` ↔ `blue sky`; applies to the loaded images. |
| Clear all tags on selected images | Select images, choose the corresponding Tool menu command and read the confirmation before continuing. |

Tag-editing tools update the in-memory data and history. Check the grid before **Save**. Selecting a few images does not restrict every batch tool to those images; the scope depends on the tool.

## 5. WD14 Tagger

Open with `Ctrl+T` or `F8`. Choose the execution mode, model, general/character tag thresholds and options such as appending to existing captions or skipping images that already have captions. Check the folder scope before running: **Include subfolders** starts at the dataset root shown in the tree.

### Run locally in TKtagger's environment

If you created `.venv` with the launcher's `--setup` option, install the inference dependencies:

```powershell
# Windows
.\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
```

```bash
# Linux
./.venv/bin/python -m pip install -r requirements-local.txt
```

Choose **Local**, enter a model repository or select a matching **ONNX** and **selected_tags.csv** pair, then run. Loading a model from a repository may require downloading files. Review the generated tags before saving captions.

### Reuse an installed tool

1. Select **Installed tool** in WD14.
2. Choose the installation folder of **kohya_ss** or **sd-scripts**.
3. Select the tool type or **Auto detect**, then click **Scan**.
4. Check the detected Python in `.venv`, `venv` or `env`. If necessary, browse to a Python executable with a working inference environment.
5. Select a detected ONNX model with its `selected_tags.csv`, or enter both paths manually.
6. Configure the tagging options and run.

This mode uses the tool's existing Python and model to run TKtagger's worker. TKtagger's GUI only needs the dependencies installed by `--setup`; the selected Python environment needs the appropriate inference libraries. If the tool or environment has moved, check the Python and model paths again.

WD14 results are stored in memory/cache for each folder, including subfolders you have not opened. Review the results, use Undo/Redo as needed and click **Save** to write captions.

## 6. Calculator: calculate repeats and export TOML

1. Open **Dataset Calculator** with `F9`.
2. Choose the trainer, caption extension and resolution, then scan the dataset folder.
3. Select the folders to include and enter ratios in row order, for example `1,2,3`.
4. Adjust batch size/epochs for the estimate, then click **Calculate**.
5. Click **Export TOML** and choose where to save the dataset configuration.

Calculator counts PNG, JPG/JPEG, WebP and BMP images directly inside each folder. Every image in an exported folder needs a caption with the selected extension. If captions are missing or image counts have changed, correct the data, scan and calculate again.

The exported file uses the schema for **kohya_ss / sd-scripts** or **Musubi Tuner**. Folder paths stay unchanged; repeats are declared in TOML. Select this file as the dataset config in your trainer. Configure the model, optimizer and actual training epochs in the trainer; Calculator's displayed step count is an estimate.

## 7. Save your workspace layout

Open **Settings → Workspace**:

- **Save:** store the current layout for restoration at startup.
- **Import / Export:** use JSON files to transfer layouts between sessions.
- **Autosave:** save after changes settle and when the application closes successfully; off by default.
- **Reset:** restore and save the default workspace.

These controls apply immediately. A workspace stores window geometry, dock positions/tabs, visibility, grid mode, card height, manual column count and tag insertion order. Dataset content and Undo/Redo history belong to the editing session and are not included in workspace files.

## 8. Save captions and dataset backup

Click **Save** or press `Ctrl+S` to write changed captions from folders held in the session. The application creates a complete snapshot of each affected folder before writing captions. Saving stops if backup fails.

Backups are stored in `.tktagger-backups` beside the dataset folder being saved. Each completed snapshot contains `data/` and `manifest.json`. A snapshot ending in `.partial` is incomplete.

To recover files, close the application, keep a copy of the current folder, copy the contents of a completed snapshot's `data/` into an empty folder and open that folder in TKtagger. Backups remain until you remove them, so keep track of available disk space.
