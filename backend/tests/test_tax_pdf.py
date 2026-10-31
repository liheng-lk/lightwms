"""Tax QR links may only resolve to an official PDF on chinatax.gov.cn."""
from django.test import SimpleTestCase

from apps.invoices.tax_pdf import TaxPdfError, next_pdf_link, validate_tax_url


class TaxPdfTests(SimpleTestCase):
    def test_rejects_non_tax_links(self):
        for url in ('http://dppt.chinatax.gov.cn/v/1', 'https://example.com/a.pdf', 'https://127.0.0.1/a.pdf'):
            with self.assertRaises(TaxPdfError):
                validate_tax_url(url)

    def test_finds_pdf_link_in_tax_page(self):
        html = '<a href="/download/invoice.pdf">下载</a>'
        self.assertEqual(
            next_pdf_link(html, 'https://dppt.example.chinatax.gov.cn/v/2'),
            'https://dppt.example.chinatax.gov.cn/download/invoice.pdf',
        )
