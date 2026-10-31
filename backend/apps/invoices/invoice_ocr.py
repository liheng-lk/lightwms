"""Read amount and party names from an invoice image.

Uses the bundled PP-OCRv4 mobile models (about 15 MB): detection, recognition,
and a tiny angle classifier. Server-size OCR models are not downloaded.
"""
from __future__ import annotations

import re
import threading
from decimal import Decimal, InvalidOperation
from io import BytesIO

_engine = None
_engine_lock = threading.Lock()

_NUMBER = re.compile(r'发票号码[:：]\s*(\d{8,20})')
_TOTAL = re.compile(r'价税合计[^\d￥¥]{0,20}[￥¥]?\s*(\d+(?:\.\d{1,2})?)')
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


def fields_from_lines(lines: list[str]) -> dict:
    text = '\n'.join(line.strip() for line in lines if line and line.strip())
    number = _NUMBER.search(text)
    buyer = _BUYER.search(text)
    seller = _SELLER.search(text)
    amount_match = _TOTAL.search(text) or _YEN.search(text)
    amount = _clean_amount(amount_match.group(1) if amount_match else None)
    invoice_number = number.group(1) if number else ''
    buyer_name = buyer.group(1) if buyer else ''
    seller_name = seller.group(1) if seller else ''
    if invoice_number and buyer_name:
        name = f'{buyer_name} 数电发票{invoice_number}'
    elif invoice_number:
        name = f'数电发票{invoice_number}'
    else:
        name = buyer_name
    return {
        'amount': amount,
        'invoice_number': invoice_number,
        'buyer_name': buyer_name,
        'seller_name': seller_name,
        'name': name[:200],
    }


def _engine_instance():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def recognize_invoice_bytes(data: bytes) -> dict:
    if not data:
        return fields_from_lines([])
    from PIL import Image, UnidentifiedImageError
    import numpy as np

    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        return fields_from_lines([])
    image = image.convert('RGB')
    image.thumbnail((1600, 1600))
    with _engine_lock:
        result, _elapsed = _engine_instance()(np.array(image))
    lines = [item[1] for item in result or [] if len(item) >= 2]
    return fields_from_lines(lines)
