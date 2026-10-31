"""QR text selection keeps only tax-bureau download links."""
from django.test import SimpleTestCase

from apps.invoices.invoice_qr import first_tax_url


class InvoiceQrTests(SimpleTestCase):
    def test_uses_tax_https_link(self):
        texts = ['not a link', 'https://dppt.zhejiang.chinatax.gov.cn:8443/v/2_26152000001052906506']
        self.assertTrue(first_tax_url(texts).startswith('https://dppt.zhejiang.chinatax.gov.cn'))

    def test_ignores_other_qr_text(self):
        self.assertIsNone(first_tax_url(['INV-1', 'http://dppt.chinatax.gov.cn/v/1']))
