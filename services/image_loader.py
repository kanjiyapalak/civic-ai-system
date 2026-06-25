from services.storage_service import guess_mime_type, load_image_bytes

__all__ = ["load_image_bytes", "guess_mime_type", "load_image_bytes_and_mime"]


def load_image_bytes_and_mime(image_ref: str) -> tuple[bytes, str]:
    data = load_image_bytes(image_ref)
    return data, guess_mime_type(image_ref)
