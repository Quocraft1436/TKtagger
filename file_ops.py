"""
file_ops.py - Operations for loading/saving tags and images
UPDATED: Uses single fixed extension (load_extension setting)
"""
import os
import time
import tempfile
from pathlib import Path
from backup_manager import backup_folder, BACKUP_DIR
from file_formats import SUPPORTED_FORMATS, normalize_caption_extension


def _get_tag_extension() -> str:
    """
    Get the tag file extension from settings.
    Returns: "txt", "cap", or custom extension
    """
    try:
        from settings_manager import settings
        ext = settings.value("load_extension", "txt")
        return normalize_caption_extension(ext or "txt")
    except ImportError:
        return "txt"


def load_tags(txt_path: str, extension: str = None) -> list:
    """
    Đọc tags từ file với extension được cài đặt.
    
    Args:
        txt_path: Đường dẫn file (base path, extension sẽ được lấy từ settings)
    
    Returns:
        list: Danh sách tags
    """
    # Lấy extension từ settings
    ext = normalize_caption_extension(extension if extension is not None else _get_tag_extension())
    
    # Thay thế extension từ base path
    base_path = os.path.splitext(txt_path)[0]
    file_path = f"{base_path}.{ext}"
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                
                # Tất cả format đều dùng comma-separated
                return [tag.strip() for tag in content.split(',') if tag.strip()]
        except Exception as e:
            print(f"[WARNING] Failed to read {file_path}: {e}")
            return []
    return []


def save_tags(txt_path: str, tags: list) -> bool:
    """
    Ghi tags vào file với extension được cài đặt.
    
    Args:
        txt_path: Đường dẫn file (base path, extension sẽ được lấy từ settings)
        tags: Danh sách tags
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    # Lấy extension từ settings
    try:
        ext = normalize_caption_extension(_get_tag_extension())
        base_path = os.path.splitext(txt_path)[0]
        file_path = f"{base_path}.{ext}"
        backup_folder(Path(file_path).parent, "save_tags")
        _write_tags(file_path, tags)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write tags for {txt_path}: {e}")
        return False


def _write_tags(file_path, tags):
    """Atomic replacement; caller must complete the folder backup first."""
    target = Path(file_path)
    normalize_caption_extension(target.suffix)
    if target.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink: {target}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=target.parent, delete=False) as f:
            temporary = f.name
            f.write(', '.join(tags))
            f.flush()
            os.fsync(f.fileno())
        if target.exists():
            os.chmod(temporary, target.stat().st_mode & 0o777)
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_folder_images(folder: str, extension: str = None) -> list:
    """
    Tải danh sách ảnh từ một thư mục.
    Tags sẽ được load dựa trên extension cài đặt (load_extension setting).
    
    Args:
        folder: Đường dẫn thư mục
    
    Returns:
        list: Danh sách dict chứa thông tin ảnh
    """
    ext = normalize_caption_extension(extension if extension is not None else _get_tag_extension())
    
    start_time = time.perf_counter()
    images = []
    try:
        for file in sorted(os.listdir(folder)):
            if file.lower().endswith(SUPPORTED_FORMATS):
                img_path = os.path.join(folder, file)
                txt_path = os.path.splitext(img_path)[0] + '.txt'  # Store base path
                tags = load_tags(txt_path, extension=ext)
                images.append({
                    'path': img_path,
                    'txt_path': txt_path,
                    'tags': tags,
                    'filename': file,
                    'modified': False,
                })
    except PermissionError:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to load folder {folder}: {e}")
        raise
    
    elapsed = time.perf_counter() - start_time
    print(f"[LOAD] {folder}")
    print(f"[LOAD] Format: .{ext}")
    print(f"[LOAD] Đã load {len(images)} ảnh trong {elapsed:.3f} giây")
    return images


def save_all_images(images: list) -> int:
    """
    Lưu tất cả ảnh đã thay đổi vào file với extension được cài đặt.
    
    Args:
        images: Danh sách dict ảnh
    
    Returns:
        int: Số file đã lưu thành công
    """
    pending = [img for img in images if img.get('modified', False)]
    ext = normalize_caption_extension(_get_tag_extension())
    # Back up all involved folders before the first write in this action.
    folders = sorted({str(Path(img['txt_path']).resolve().parent) for img in pending})
    for folder in folders:
        backup_folder(folder, "save_all_images")
    count = 0
    for img in pending:
        file_path = os.path.splitext(img['txt_path'])[0] + '.' + ext
        _write_tags(file_path, img['tags'])
        img['modified'] = False
        count += 1
    return count


def populate_folder_tree(path: str) -> dict:
    """
    Tạo cấu trúc cây thư mục đệ quy.
    Trả về dict {path: [child_paths]}
    
    Args:
        path: Đường dẫn gốc
    
    Returns:
        dict: Cấu trúc cây thư mục
    """
    start_time = time.perf_counter()
    tree = {}
    try:
        children = []
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and item != BACKUP_DIR:
                children.append(item_path)
                tree.update(populate_folder_tree(item_path))
        tree[path] = children
    except PermissionError:
        tree[path] = []
    except Exception as e:
        print(f"[ERROR] Failed to populate tree for {path}: {e}")
        tree[path] = []
    
    # Chỉ in thời gian ở lần gọi ngoài cùng
    if path:
        elapsed = time.perf_counter() - start_time
        print(f"[TREE] {path} - {elapsed:.3f} giây")
    return tree
