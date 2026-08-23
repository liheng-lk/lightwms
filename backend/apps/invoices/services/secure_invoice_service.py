"""Security-hardened invoice service.

The legacy service already checks extension and size.  This subclass adds
content-signature checks so a renamed executable/text file cannot be accepted
simply because it ends in .pdf/.jpg/.jpeg/.png.
"""
from core.exceptions import BusinessConflictError

from .invoice_service import InvoiceService as BaseInvoiceService


class InvoiceService(BaseInvoiceService):
    """Invoice service with file magic-byte validation."""

    @classmethod
    def _validate_file(cls, file, filename: str) -> str:
        ext = super()._validate_file(file, filename)

        header = file.read(16)
        file.seek(0)

        valid = False
        if ext == '.pdf':
            valid = header.startswith(b'%PDF-')
        elif ext == '.png':
            valid = header.startswith(b'\x89PNG\r\n\x1a\n')
        elif ext in {'.jpg', '.jpeg'}:
            valid = header.startswith(b'\xff\xd8\xff')

        if not valid:
            raise BusinessConflictError(
                code='INVALID_FILE_CONTENT',
                message='File content does not match the declared invoice file type.',
                details={'filename': filename, 'extension': ext},
            )

        return ext
