"""
file_ops.py - Thao tác đọc/ghi file tags
"""
import os


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')


def load_tags(txt_path: str) -> list:
    """Đọc tags từ file .txt."""
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return [tag.strip() for tag in content.split(',') if tag.strip()]
        except Exception:
            return []
    return []


def save_tags(txt_path: str, tags: list) -> bool:
    """Ghi tags vào file .txt. Trả về True nếu thành công."""
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(', '.join(tags))
        return True
    except Exception:
        return False


def load_folder_images(folder: str) -> list:
    """Tải danh sách ảnh từ một thư mục."""
    images = []
    try:
        for file in sorted(os.listdir(folder)):
            if file.lower().endswith(SUPPORTED_FORMATS):
                img_path = os.path.join(folder, file)
                txt_path = os.path.splitext(img_path)[0] + '.txt'
                tags = load_tags(txt_path)
                images.append({
                    'path': img_path,
                    'txt_path': txt_path,
                    'tags': tags,
                    'filename': file,
                    'modified': False,
                })
    except PermissionError:
        raise
    return images


def save_all_images(images: list) -> int:
    """Lưu tất cả ảnh đã thay đổi. Trả về số file đã lưu."""
    count = 0
    for img in images:
        if img.get('modified', False):
            if save_tags(img['txt_path'], img['tags']):
                img['modified'] = False
                count += 1
    return count


def populate_folder_tree(path: str) -> dict:
    """Tạo cấu trúc cây thư mục đệ quy.
    Trả về dict {path: [child_paths]}
    """
    tree = {}
    try:
        children = []
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                children.append(item_path)
                tree.update(populate_folder_tree(item_path))
        tree[path] = children
    except PermissionError:
        tree[path] = []
    return tree
