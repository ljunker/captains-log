from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from app.config import settings


register_heif_opener()

IMAGE_MIME_BY_EXTENSION = {
    ".dng": "image/x-adobe-dng",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}
IMAGE_EXTENSIONS = frozenset(IMAGE_MIME_BY_EXTENSION)
IMAGE_MIME_TYPES = frozenset(IMAGE_MIME_BY_EXTENSION.values()) | {"image/dng"}
THUMBNAIL_CAPABLE_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".dng"})
RAW_IMAGE_EXTENSIONS = frozenset({".dng"})

AUDIO_MIME_BY_EXTENSION = {
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
}
AUDIO_EXTENSIONS = frozenset(AUDIO_MIME_BY_EXTENSION)
AUDIO_MIME_TYPES = frozenset(AUDIO_MIME_BY_EXTENSION.values()) | {"audio/x-m4a"}

MAX_IMAGE_FILE_SIZE = 100 * 1024 * 1024
MAX_AUDIO_FILE_SIZE = 40 * 1024 * 1024
THUMBNAIL_SIZE = (480, 480)


def ensure_upload_directories() -> None:
    (settings.uploads_path / "originals").mkdir(parents=True, exist_ok=True)
    (settings.uploads_path / "thumbnails").mkdir(parents=True, exist_ok=True)


def normalized_extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def image_mime_type_for_filename(filename: str | None) -> str | None:
    return IMAGE_MIME_BY_EXTENSION.get(normalized_extension(filename))


def audio_mime_type_for_filename(filename: str | None) -> str | None:
    return AUDIO_MIME_BY_EXTENSION.get(normalized_extension(filename))


def build_storage_key(prefix: str, filename: str | None) -> str:
    extension = normalized_extension(filename)
    return f"{prefix}/{uuid4().hex}{extension}"


def storage_path(storage_key: str) -> Path:
    return settings.uploads_path / storage_key


def thumbnail_storage_key() -> str:
    return f"thumbnails/{uuid4().hex}.jpg"


def can_generate_thumbnail(filename: str | None, mime_type: str) -> bool:
    return normalized_extension(filename) in THUMBNAIL_CAPABLE_IMAGE_EXTENSIONS and mime_type in IMAGE_MIME_TYPES


def is_raw_image(filename: str | None) -> bool:
    return normalized_extension(filename) in RAW_IMAGE_EXTENSIONS


def create_image_thumbnail(source_bytes: bytes, filename: str | None = None) -> bytes:
    if is_raw_image(filename):
        image = _open_raw_preview(source_bytes)
    else:
        image = Image.open(BytesIO(source_bytes))

    with image:
        normalized = ImageOps.exif_transpose(image)
        if "A" in normalized.getbands():
            rgba_image = normalized.convert("RGBA")
            background = Image.new("RGB", rgba_image.size, "#ffffff")
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            normalized = background
        elif normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
        thumbnail = normalized.copy()
        thumbnail.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        thumbnail.save(buffer, format="JPEG", quality=82, optimize=True)
        return buffer.getvalue()


def _open_raw_preview(source_bytes: bytes) -> Image.Image:
    import rawpy

    with rawpy.imread(BytesIO(source_bytes)) as raw:
        try:
            thumbnail = raw.extract_thumb()
            if thumbnail.format == rawpy.ThumbFormat.JPEG:
                return Image.open(BytesIO(thumbnail.data))
            if thumbnail.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumbnail.data)
        except rawpy.LibRawNoThumbnailError:
            pass

        rgb = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=True)
        return Image.fromarray(rgb)


def file_url(attachment_id: int) -> str:
    root_path = settings.root_path or ""
    return f"{root_path}/api/attachments/{attachment_id}/file" if root_path else f"/api/attachments/{attachment_id}/file"


def thumbnail_url(attachment_id: int) -> str:
    root_path = settings.root_path or ""
    return (
        f"{root_path}/api/attachments/{attachment_id}/thumbnail"
        if root_path
        else f"/api/attachments/{attachment_id}/thumbnail"
    )
