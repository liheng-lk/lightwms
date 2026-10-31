"""Recognize invoice fields from an uploaded image."""
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsItemManagerOrSuperAdmin

from .invoice_ocr import recognize_invoice_bytes

MAX_IMAGE_BYTES = 10 * 1024 * 1024


class InvoiceRecognizeView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                {'code': 'INVOICE_OCR_ERROR', 'message': '请上传发票图片。', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > MAX_IMAGE_BYTES:
            return Response(
                {'code': 'INVOICE_OCR_ERROR', 'message': '图片不能超过 10MB。', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            fields = recognize_invoice_bytes(upload.read())
        except Exception:
            return Response(
                {'code': 'INVOICE_OCR_ERROR', 'message': '发票识别失败，请手填金额。', 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(fields)
