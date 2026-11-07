"""Shared image formats and validation for caption file extensions."""
import re


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.avif')


def normalize_caption_extension(extension):
    """Return a bare caption extension, rejecting image formats and paths."""
    ext = str(extension).strip().lstrip('.').lower()
    if '.' + ext in SUPPORTED_FORMATS:
        raise ValueError('Caption extension must not be an image format.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', ext):
        raise ValueError('Enter a caption extension using letters, digits, hyphens or underscores.')
    return ext
