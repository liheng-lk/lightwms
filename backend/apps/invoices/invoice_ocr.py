"""Read amount and party names from an invoice image or PDF.

Images use the bundled PP-OCRv4 mobile models (about 15 MB). PDFs use the
text layer first; a scanned PDF falls back to rendering page one and OCR.
"""
from __future__ import annotations

import re
import threading
from decimal import Decimal, InvalidOperation
from io import BytesIO

_engine = None
_engine_lock = threading.Lock()

_NUMBER = re.compile(r'发票号码[:：]\s*(\d{8,20})')
_TOTAL_LINE = re.compile(r'价税合计[^\n]{0,120}')
_DECIMAL = re.compile(r'(\d+\.\d{2})')
_YEN = re.compile(r'[￥¥]\s*(\d+\.\d{2})')
_BUYER = re.compile(r'(?:购买方名称|购方名称)[:：]\s*(\S+)')
_SELLER = re.compile(r'(?:销售方名称|销方名称)[:：]\s*(\S+)')


def _clean_amount(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if value < 0 or value.copy_abs() >= Decimal('10000000000'):
        return None
    return f'{value:.2f}'


def _amount_from_text(text: str) -> str | None:
    """Use the last amount on a 价税合计 line, not an earlier line-item amount."""
    for line in reversed(list(_TOTAL_LINE.finditer(text))):
        amounts = _DECIMAL.findall(line.group(0))
        if amounts:
            return _clean_amount(amounts[-1])
    yens = list(_YEN.finditer(text))
    if yens:
        return _clean_amount(yens[-1].group(1))
    return None


def _named(fields: dict) -> dict:
    number = fields.get('invoice_number') or ''
    buyer = fields.get('buyer_name') or ''
    if number and buyer:
        fields['name'] = f'{buyer} 数电发票{number}'[:200]
    elif number:
        fields['name'] = f'数电发票{number}'
    else:
        fields['name'] = buyer[:200]
    return fields


def _fill_missing(primary: dict, extra: dict) -> dict:
    merged = dict(primary)
    for key in ('amount', 'invoice_number', 'buyer_name', 'seller_name'):
        if not merged.get(key) and extra.get(key):
            merged[key] = extra[key]
    return _named(merged)


def fields_from_lines(lines: list[str]) -> dict:
    text = '\n'.join(line.strip() for line in lines if line and line.strip())
    number = _NUMBER.search(text)
    buyer = _BUYER.search(text)
    seller = _SELLER.search(text)
    amount = _amount_from_text(text)
    invoice_number = number.group(1) if number else ''
    buyer_name = buyer.group(1) if buyer else ''
    seller_name = seller.group(1) if seller else ''
    return _named({
        'amount': amount,
        'invoice_number': invoice_number,
        'buyer_name': buyer_name,
        'seller_name': seller_name,
        'name': '',
    })


def _engine_instance():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def _ocr_image(image) -> dict:
    import numpy as np
    from PIL import ImageOps

    image = ImageOps.exif_transpose(image) or image
    image = image.convert('RGB')
    image.thumbnail((1600, 1600))
    with _engine_lock:
        result, _elapsed = _engine_instance()(np.array(image))
    lines = [item[1] for item in result or [] if len(item) >= 2]
    return fields_from_lines(lines)


def _pdf_text(data: bytes) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt('')
        except Exception:
            return fields_from_lines([])
    lines = []
    for page in reader.pages[:2]:
        lines.extend((page.extract_text() or '').splitlines())
    return fields_from_lines(lines)


def _pdf_first_page_image(data: bytes):
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        if len(document) < 1:
            return None
        bitmap = document[0].render(scale=2)
        try:
            return bitmap.to_pil()
        finally:
            bitmap.close()
    finally:
        document.close()


def recognize_invoice_bytes(data: bytes) -> dict:
    if not data:
        return fields_from_lines([])
    if data[:5] == b'%PDF-':
        try:
            fields = _pdf_text(data)
        except Exception:
            fields = fields_from_lines([])
        if fields['amount']:
            return fields
        try:
            image = _pdf_first_page_image(data)
        except Exception:
            return fields
        if image is None:
            return fields
        return _fill_missing(fields, _ocr_image(image))

    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        return fields_from_lines([])
    return _ocr_image(image)
