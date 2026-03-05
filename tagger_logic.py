"""
tagger_logic.py – WD14 Tagger backend for TKtagger

Supports:
  - Loading model from HuggingFace Hub (repo_id) OR local .onnx file
  - PNG alpha → white background flattening in /tmp before inference
  - Output as  tag_<stem><ext>  or overwrite existing caption file
  - Subfolder recursion from root_folder
  - Progress callback  cb(current, total, message)  for UI integration

Usage (standalone / test):
    from tagger_logic import run_tagger
    run_tagger(config, progress_cb=print)

Usage (from main_window slot):
    def _on_tagging_started(self, config):
        from tagger_logic import run_tagger
        from threading import Thread
        Thread(target=run_tagger, args=(config, self._tagger_progress), daemon=True).start()
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional

# gradio_client – only needed for API mode
try:
    from gradio_client import Client as GradioClient
    _HAS_GRADIO_CLIENT = True
except ImportError:
    _HAS_GRADIO_CLIENT = False

import numpy as np
from PIL import Image

# ──────────────────────────────────────────────────────────────
#  Optional heavy imports – only needed at inference time
# ──────────────────────────────────────────────────────────────
try:
    import onnxruntime as ort
    print(f"Available providers: {ort.get_available_providers()}")
    _HAS_ORT = True
except ImportError:
    _HAS_ORT = False

# HuggingFace hub – optional, only for remote download path
try:
    from huggingface_hub import hf_hub_download
    _HAS_HF = True
except ImportError:
    _HAS_HF = False


# ──────────────────────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────────────────────
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MODEL_FILENAME   = "model.onnx"
TAGS_FILENAME    = "selected_tags.csv"
MODEL_INPUT_SIZE = 512   # WD14 standard input resolution

RATING_TAGS = {
    "general":    "rating:general",
    "sensitive":  "rating:sensitive",
    "questionable": "rating:questionable",
    "explicit":   "rating:explicit",
}

# ──────────────────────────────────────────────────────────────
#  Public entry point
# ──────────────────────────────────────────────────────────────

def run_tagger(
    config: dict,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[dict]:
    """
    Run WD14 tagging according to *config* (produced by WaifuTaggerWindow).

    Parameters
    ----------
    config       : dict from WaifuTaggerWindow.tagging_started signal
    progress_cb  : optional callable(current, total, message)

    Returns
    -------
    List of dicts: [{"path": str, "tags": [str], "skipped": bool, "error": str|None}]
    """
    _cb = progress_cb or (lambda *_: None)

    # 1. Validate dependencies
    if not _HAS_ORT:
        raise ImportError(
            "onnxruntime is not installed.\n"
            "Install it with:  pip install onnxruntime  (or onnxruntime-gpu)"
        )

    # 2. Resolve model & tags CSV
    _cb(0, 0, "Loading model…")
    onnx_path, csv_path = _resolve_model(config)

    # 3. Load tags list
    tags_df = _load_tags_csv(csv_path)               # list of dicts: name, category
    rating_idxs, general_idxs, char_idxs = _split_tag_indices(tags_df)

    # 4. Load ONNX session
    session = _load_session(onnx_path)
    input_name = session.get_inputs()[0].name

    # 5. Collect image paths
    image_paths = _collect_images(config)
    total = len(image_paths)
    if total == 0:
        _cb(0, 0, "No images found.")
        return []

    # 6. Prepare /tmp scratch dir for alpha conversion
    tmp_dir = Path(tempfile.mkdtemp(prefix="tktagger_")) if config.get("alpha_to_white") else None

    results = []
    try:
        for idx, img_path in enumerate(image_paths):
            img_path = Path(img_path)
            _cb(idx, total, f"[{idx+1}/{total}] {img_path.name}")

            try:
                # 6a. Flatten alpha if needed
                work_path = _flatten_alpha(img_path, tmp_dir) if config.get("alpha_to_white") else img_path

                # 6b. Preprocess → numpy
                img_tensor = _preprocess_image(work_path)

                # 6c. Run inference
                probs = session.run(None, {input_name: img_tensor})[0][0]   # shape (num_tags,)

                # 6d. Decode tags
                tags = _decode_tags(
                    probs        = probs,
                    tags_df      = tags_df,
                    rating_idxs  = rating_idxs,
                    general_idxs = general_idxs,
                    char_idxs    = char_idxs,
                    config       = config,
                )

                # 6e. Write caption file
                out_path = _caption_path(img_path, config)
                _write_caption(out_path, tags, config)

                results.append({"path": str(img_path), "tags": tags, "skipped": False, "error": None})

            except Exception as exc:
                results.append({"path": str(img_path), "tags": [], "skipped": True, "error": str(exc)})

    finally:
        # Clean up /tmp scratch
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    _cb(total, total, f"Done – {total} images processed.")
    return results

def run_tagger_api(
    config: dict,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> list[dict] | None:
    """
    Run WD14 tagging via the Kohya_ss Gradio API (/caption_images_3).

    Requires:  pip install gradio_client

    The kohya_ss API does NOT return per-image tag lists — it writes caption
    files directly into *train_data_dir* on the server side.  Therefore this
    function returns None (no in-memory results to merge back into the UI).
    The caller in main_window._on_tagging_started already handles None gracefully.

    Parameters
    ----------
    config       : dict produced by WaifuTaggerWindow.tagging_started
    progress_cb  : optional callable(current, total, message)
    """
    _cb = progress_cb or (lambda *_: None)

    if not _HAS_GRADIO_CLIENT:
        raise ImportError(
            "gradio_client is not installed.\n"
            "Install with:  pip install gradio_client"
        )

    base_url = config.get("api_url", "http://127.0.0.1:7860").rstrip("/")

    # ── Build the 22 named parameters exactly as documented ───────────────
    # Source: kohya_ss /caption_images_3  (api_name="/caption_images_3")
    train_data_dir   = config.get("target_folder", "")
    caption_extension = config.get("ext", ".txt")          # ".cap" | ".caption" | ".txt"
    batch_size       = float(config.get("batch_size", 1))
    general_threshold = float(config.get("gen_threshold", 0.35))
    character_threshold = float(config.get("char_threshold", 0.35))
    repo_id          = config.get("repo_id", "SmilingWolf/wd-v1-4-convnextv2-tagger-v2")
    recursive        = bool(config.get("include_subfolders", False))
    max_workers      = float(config.get("max_data_loader_n_workers", 2))
    debug            = bool(config.get("debug", True))
    undesired_tags   = ", ".join(config.get("undesired_tags", []))
    frequency_tags   = bool(config.get("frequency_tags", True))
    always_first_tags = ", ".join(config.get("prefix_tags", []))
    use_onnx         = True                                 # always True for speed
    append_tags      = bool(config.get("append_tags", False))
    force_download   = bool(config.get("force_download", False))
    caption_separator = config.get("separator", ", ")
    tag_replacement  = config.get("tag_replacement", "")   # "old1,new1;old2,new2" or ""
    character_tag_expand = bool(config.get("char_expand", False))
    use_rating_tags  = bool(config.get("use_rating", False))
    use_rating_tags_as_last_tag = bool(config.get("rating_as_last", False))
    remove_underscore = bool(config.get("remove_underscore", True))
    thresh           = float(config.get("gen_threshold", 0.35))   # global fallback threshold

    try:
        _cb(0, 1, f"Đang kết nối tới Kohya_ss tại {base_url} …")
        client = GradioClient(base_url)

        _cb(0, 1, f"Đang gửi yêu cầu tagging cho: {train_data_dir}")
        result = client.predict(
            train_data_dir=train_data_dir,
            caption_extension=caption_extension,
            batch_size=batch_size,
            general_threshold=general_threshold,
            character_threshold=character_threshold,
            repo_id=repo_id,
            recursive=recursive,
            max_data_loader_n_workers=max_workers,
            debug=debug,
            undesired_tags=undesired_tags,
            frequency_tags=frequency_tags,
            always_first_tags=always_first_tags,
            onnx=use_onnx,
            append_tags=append_tags,
            force_download=force_download,
            caption_separator=caption_separator,
            tag_replacement=tag_replacement,
            character_tag_expand=character_tag_expand,
            use_rating_tags=use_rating_tags,
            use_rating_tags_as_last_tag=use_rating_tags_as_last_tag,
            remove_underscore=remove_underscore,
            thresh=thresh,
            api_name="/caption_images_3",
        )

        _cb(1, 1, f"Kohya_ss hoàn thành! Kết quả: {result}")
        # kohya_ss trả về 1 phần tử (thường là chuỗi log).
        # Caption files đã được ghi vào disk bởi server — không có list tags trả về.
        return None

    except Exception as exc:
        _cb(0, 1, f"Lỗi khi gọi Kohya_ss API: {exc}")
        raise

# ──────────────────────────────────────────────────────────────
#  Model resolution
# ──────────────────────────────────────────────────────────────

def _resolve_model(config: dict) -> tuple[str, str]:
    """Return (onnx_path, csv_path) – download from HF if needed."""

    local_onnx = config.get("onnx_path")
    local_csv  = config.get("csv_path")

    if local_onnx and os.path.isfile(local_onnx):
        # Local ONNX provided
        if local_csv and os.path.isfile(local_csv):
            return local_onnx, local_csv
        # Try sibling selected_tags.csv
        sibling = os.path.join(os.path.dirname(local_onnx), TAGS_FILENAME)
        if os.path.isfile(sibling):
            return local_onnx, sibling
        raise FileNotFoundError(
            f"ONNX model found but tags CSV not found.\n"
            f"Expected at: {sibling}\n"
            f"Please provide it via the 'Tags CSV' field."
        )

    # Download from HuggingFace Hub
    if not _HAS_HF:
        raise ImportError(
            "huggingface_hub is not installed.\n"
            "Install with:  pip install huggingface_hub\n"
            "Or provide a local ONNX file instead."
        )

    repo_id      = config.get("repo_id", "SmilingWolf/wd-v1-4-convnextv2-tagger-v2")
    force        = config.get("force_download", False)
    cache_kwargs = {"force_download": force} if force else {}

    onnx_path = hf_hub_download(repo_id, MODEL_FILENAME, **cache_kwargs)
    csv_path  = hf_hub_download(repo_id, TAGS_FILENAME,  **cache_kwargs)
    return onnx_path, csv_path


# ──────────────────────────────────────────────────────────────
#  Tags CSV
# ──────────────────────────────────────────────────────────────

def _load_tags_csv(csv_path: str) -> list[dict]:
    """Load selected_tags.csv → list of {name, category}."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({"name": row["name"], "category": int(row.get("category", 0))})
    return rows


def _split_tag_indices(tags_df: list[dict]) -> tuple[list[int], list[int], list[int]]:
    """
    WD14 categories:
      9  = rating
      0  = general
      4  = character
    Returns three index lists.
    """
    rating_idxs  = [i for i, t in enumerate(tags_df) if t["category"] == 9]
    general_idxs = [i for i, t in enumerate(tags_df) if t["category"] == 0]
    char_idxs    = [i for i, t in enumerate(tags_df) if t["category"] == 4]
    return rating_idxs, general_idxs, char_idxs


# ──────────────────────────────────────────────────────────────
#  ONNX session
# ──────────────────────────────────────────────────────────────

def _load_session(onnx_path: str) -> "ort.InferenceSession":
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    try:
        return ort.InferenceSession(onnx_path, providers=providers)
    except Exception:
        # Fallback to CPU only
        return ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])


# ──────────────────────────────────────────────────────────────
#  Image pre-processing
# ──────────────────────────────────────────────────────────────

def _flatten_alpha(src: Path, tmp_dir: Path) -> Path:
    """
    If *src* has an alpha channel, composite it over white and save
    a JPEG/PNG to *tmp_dir*.  Returns the work path.
    If no alpha, returns *src* unchanged.
    """
    with Image.open(src) as img:
        if img.mode not in ("RGBA", "LA") and not (
            img.mode == "P" and "transparency" in img.info
        ):
            return src   # no alpha, nothing to do

        # Convert to RGBA to handle palette transparency
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[3])   # alpha as mask
        flat = background.convert("RGB")

        dest = tmp_dir / (src.stem + "_flat.png")
        flat.save(dest, format="PNG")
        return dest


def _preprocess_image(path: Path) -> np.ndarray:
    """
    Load image, resize to MODEL_INPUT_SIZE×MODEL_INPUT_SIZE,
    convert to float32 RGB, return shape (1, H, W, 3).
    WD14 expects BGR channel order (OpenCV convention).
    """
    with Image.open(path) as img:
        img = img.convert("RGB")

        # Pad to square then resize (preserve aspect ratio with padding)
        img = _pad_to_square(img)
        img = img.resize((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), Image.BICUBIC)

        arr = np.array(img, dtype=np.float32)        # H,W,3  RGB
        arr = arr[:, :, ::-1]                        # RGB → BGR
        arr = np.expand_dims(arr, axis=0)            # 1,H,W,3
    return arr


def _pad_to_square(img: Image.Image, fill: int = 255) -> Image.Image:
    w, h = img.size
    if w == h:
        return img
    size = max(w, h)
    canvas = Image.new("RGB", (size, size), (fill, fill, fill))
    canvas.paste(img, ((size - w) // 2, (size - h) // 2))
    return canvas


# ──────────────────────────────────────────────────────────────
#  Tag decoding
# ──────────────────────────────────────────────────────────────

def _decode_tags(
    probs:        np.ndarray,
    tags_df:      list[dict],
    rating_idxs:  list[int],
    general_idxs: list[int],
    char_idxs:    list[int],
    config:       dict,
) -> list[str]:
    gen_thresh  = float(config.get("gen_threshold",  0.35))
    char_thresh = float(config.get("char_threshold", 0.35))
    remove_us   = config.get("remove_underscore", True)
    char_expand = config.get("char_expand", False)
    use_rating  = config.get("use_rating", False)
    rating_last = config.get("rating_as_last", False)
    undesired   = set(config.get("undesired_tags", []))
    prefix_tags = list(config.get("prefix_tags", []))
    rep_map     = config.get("replacement_map", {})

    # ── character tags ────────────────────────────
    char_tags: list[str] = []
    for i in char_idxs:
        if probs[i] >= char_thresh:
            name = _clean_tag(tags_df[i]["name"], remove_us)
            if char_expand:
                name = _expand_parens(name)
            char_tags.append(name)

    # ── general tags ──────────────────────────────
    gen_tags: list[str] = []
    for i in general_idxs:
        if probs[i] >= gen_thresh:
            name = _clean_tag(tags_df[i]["name"], remove_us)
            gen_tags.append(name)

    # ── rating tag ────────────────────────────────
    rating_tag: list[str] = []
    if use_rating and rating_idxs:
        best_idx = max(rating_idxs, key=lambda i: probs[i])
        raw_name = tags_df[best_idx]["name"]
        rating_tag = [RATING_TAGS.get(raw_name, raw_name)]

    # ── assemble ──────────────────────────────────
    all_tags: list[str] = char_tags + gen_tags
    if use_rating and not rating_last:
        all_tags = rating_tag + all_tags
    elif use_rating and rating_last:
        all_tags = all_tags + rating_tag

    # Apply replacement map
    all_tags = [rep_map.get(t, t) for t in all_tags]

    # Remove undesired
    all_tags = [t for t in all_tags if t not in undesired]

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for t in all_tags:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    # Prepend prefix tags
    result: list[str] = []
    for p in prefix_tags:
        if p and p not in seen:
            result.append(p)
    result.extend(deduped)

    return result


def _clean_tag(name: str, remove_underscore: bool) -> str:
    if remove_underscore:
        name = name.replace("_", " ")
    return name.strip()


def _expand_parens(name: str) -> str:
    """
    Convert 'character_(series)' style to 'character, series'.
    e.g. 'hatsune_miku_(vocaloid)' → 'hatsune miku, vocaloid'
    """
    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        return f", {inner}"
    return re.sub(r"\(([^)]+)\)", repl, name).strip(", ")


# ──────────────────────────────────────────────────────────────
#  Caption file I/O
# ──────────────────────────────────────────────────────────────

def _caption_path(img_path: Path, config: dict) -> Path:
    ext  = config.get("ext", ".txt")
    stem = img_path.stem
    filename = f"{stem}{ext}"

    return img_path.parent / filename


def _write_caption(
    out_path: Path,
    tags:     list[str],
    config:   dict,
) -> None:
    sep       = config.get("separator", ", ")
    append    = config.get("append_tags", False)

    if append and out_path.exists():
        existing_text = out_path.read_text(encoding="utf-8").strip()
        existing_tags = [t.strip() for t in existing_text.split(",") if t.strip()]
        # merge: keep existing, append new ones that aren't already there
        existing_set = set(existing_tags)
        merged = existing_tags + [t for t in tags if t not in existing_set]
        content = sep.join(merged)
    else:
        content = sep.join(tags)

    out_path.write_text(content, encoding="utf-8")


# ──────────────────────────────────────────────────────────────
#  Image collection
# ──────────────────────────────────────────────────────────────

def _collect_images(config: dict) -> list[Path]:
    """
    Return sorted list of image paths to process.

    include_subfolders=False  → only config["target_folder"]
    include_subfolders=True   → all subdirs under config["root_folder"]
    """
    include_sub   = config.get("include_subfolders", False)
    target_folder = Path(config.get("target_folder", ""))
    root_folder   = Path(config.get("root_folder", target_folder))

    if include_sub:
        base = root_folder if root_folder.is_dir() else target_folder
        paths: list[Path] = []
        for dirpath, _dirs, files in os.walk(base):
            for f in sorted(files):
                p = Path(dirpath) / f
                if p.suffix.lower() in IMAGE_EXTENSIONS:
                    paths.append(p)
        return paths
    else:
        folder = target_folder if target_folder.is_dir() else root_folder
        return sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )


# ──────────────────────────────────────────────────────────────
#  Convenience: check environment
# ──────────────────────────────────────────────────────────────

def check_dependencies() -> dict[str, bool]:
    """Return dict of required package availability for UI diagnostics."""
    return {
        "onnxruntime":    _HAS_ORT,
        "huggingface_hub": _HAS_HF,
        "PIL":            True,   # always required; import would have failed already
        "numpy":          True,
    }


# ──────────────────────────────────────────────────────────────
#  Quick CLI test
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json, sys

    test_config = {
        "repo_id":            "SmilingWolf/wd-v1-4-convnextv2-tagger-v2",
        "onnx_path":          None,
        "csv_path":           None,
        "force_download":     False,
        "ext":                ".txt",
        "separator":          ", ",
        "tag_prefix_output":  True,
        "alpha_to_white":     True,
        "target_folder":      sys.argv[1] if len(sys.argv) > 1 else ".",
        "root_folder":        sys.argv[1] if len(sys.argv) > 1 else ".",
        "include_subfolders": False,
        "gen_threshold":      0.35,
        "char_threshold":     0.35,
        "char_expand":        False,
        "remove_underscore":  True,
        "append_tags":        False,
        "use_rating":         True,
        "rating_as_last":     True,
        "prefix_tags":        [],
        "undesired_tags":     [],
        "replacement_map":    {},
    }

    def progress(cur, total, msg):
        print(f"[{cur}/{total}] {msg}")

    results = run_tagger(test_config, progress_cb=progress)
    print(json.dumps(results, indent=2, ensure_ascii=False))
