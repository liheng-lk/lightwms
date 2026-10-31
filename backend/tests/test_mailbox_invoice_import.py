"""Mailbox secret handling and attachment extraction. No live IMAP."""
from email.message import EmailMessage

from django.test import SimpleTestCase, override_settings

from apps.invoices.mailbox_crypto import decrypt_secret, encrypt_secret
from apps.invoices.mailbox_imap import attachments_from_message, resolve_endpoint
from apps.invoices.models import MailboxProvider


@override_settings(SECRET_KEY='mailbox-test-secret')
class MailboxCryptoTests(SimpleTestCase):
    def test_round_trip_hides_plaintext(self):
        token = encrypt_secret('auth-code-123456')
        self.assertNotIn('auth-code-123456', token)
        self.assertEqual(decrypt_secret(token), 'auth-code-123456')

    def test_presets_and_custom_host(self):
        self.assertEqual(resolve_endpoint(MailboxProvider.QQ), ('imap.qq.com', 993))
        self.assertEqual(resolve_endpoint(MailboxProvider.CUSTOM, 'imap.example.com', 993), ('imap.example.com', 993))

    def test_extracts_only_invoice_files(self):
        message = EmailMessage()
        message['Subject'] = '发票'
        message['From'] = 'billing@example.com'
        message.set_content('see attachment')
        message.add_attachment(b'%PDF-1.4 invoice', maintype='application', subtype='pdf', filename='invoice.pdf')
        message.add_attachment(b'not-an-invoice', maintype='text', subtype='plain', filename='notes.txt')
        found = attachments_from_message(message.as_bytes())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['filename'], 'invoice.pdf')
        self.assertTrue(found[0]['content'].startswith(b'%PDF-'))
