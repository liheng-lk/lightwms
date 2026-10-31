"""Read a tax-bureau URL from an invoice QR image."""
from __future__ import annotations

from io import BytesIO


def first_tax_url(texts: list[str]) -> str | None:
    for text in texts:
        value = (text or '').strip()
        lowered = value.lower()
        if lowered.startswith('https://') and 'chinatax.gov.cn' in lowered:
            return value
    return None


def tax_url_from_image(data: bytes) -> str | None:
    if not data or data[:5] == b'%PDF-':
        return None
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError:
        return None
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        return None
    image = ImageOps.exif_transpose(image) or image
    image = image.convert('RGB')
    array = np.array(image)
    detector = cv2.QRCodeDetector()
    found: list[str] = []
    try:
        ok, decoded, _points, _straight = detector.detectAndDecodeMulti(array)
        if ok and decoded is not None:
            found.extend(str(item) for item in decoded if item)
    except cv2.error:
        found = []
    if not found:
        try:
            single, _points, _straight = detector.detectAndDecode(array)
        except cv2.error:
            single = ''
        if single:
            found.append(str(single))
    return first_tax_url(found)
