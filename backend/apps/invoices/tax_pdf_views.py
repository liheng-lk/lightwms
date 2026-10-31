"""Return the official tax-bureau PDF for a QR link. Never stores the QR image."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import quote

from core.permissions import IsItemManagerOrSuperAdmin

from .tax_pdf import TaxPdfError, download_tax_pdf


class InvoiceTaxPdfView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request):
        url = str(request.data.get('url') or '')
        try:
            payload, filename = download_tax_pdf(url)
        except TaxPdfError as exc:
            return Response(
                {'code': 'TAX_PDF_ERROR', 'message': str(exc), 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = HttpResponse(payload, content_type='application/pdf')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response
