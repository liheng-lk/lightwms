"""
URL configuration for invoices app.
"""
from django.urls import path

from .advanced_views import (
    InvoiceListCreateView,
    InvoiceExportView,
    ReimbursementExcelExportView,
)
from .hardened_views import (
    InvoiceDetailView,
    InvoiceBatchStatusUpdateView,
    InvoiceBatchDeleteView,
)
from .metadata_views import InvoiceUploadersView
from .permission_views import (
    InvoiceStatusUpdateView,
    InvoiceCategoriesView,
    InvoiceMonthsView,
)
from .mailbox_views import (
    MailboxAttachmentListView,
    MailboxDetailView,
    MailboxImportView,
    MailboxListCreateView,
    MailboxRecognizeView,
)
from .ocr_views import InvoiceRecognizeView
from .tax_pdf_views import InvoiceTaxPdfView
from .private_views import PrivateInvoiceFileView

urlpatterns = [
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list-create'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/status/', InvoiceStatusUpdateView.as_view(), name='invoice-status-update'),
    path('invoices/batch/status/', InvoiceBatchStatusUpdateView.as_view(), name='invoice-batch-status'),
    path('invoices/batch/delete/', InvoiceBatchDeleteView.as_view(), name='invoice-batch-delete'),
    path('invoices/export/', InvoiceExportView.as_view(), name='invoice-export'),
    path(
        'invoices/export/reimbursement/',
        ReimbursementExcelExportView.as_view(),
        name='invoice-reimbursement-export',
    ),
    path('invoices/categories/', InvoiceCategoriesView.as_view(), name='invoice-categories'),
    path('invoices/months/', InvoiceMonthsView.as_view(), name='invoice-months'),
    path('invoices/uploaders/', InvoiceUploadersView.as_view(), name='invoice-uploaders'),
    path('invoices/recognize/', InvoiceRecognizeView.as_view(), name='invoice-recognize'),
    path('invoices/tax-pdf/', InvoiceTaxPdfView.as_view(), name='invoice-tax-pdf'),
    path('mailboxes/', MailboxListCreateView.as_view(), name='mailbox-list-create'),
    path('mailboxes/<int:pk>/', MailboxDetailView.as_view(), name='mailbox-detail'),
    path('mailboxes/<int:pk>/attachments/', MailboxAttachmentListView.as_view(), name='mailbox-attachments'),
    path('mailboxes/<int:pk>/import/', MailboxImportView.as_view(), name='mailbox-import'),
    path('mailboxes/<int:pk>/recognize/', MailboxRecognizeView.as_view(), name='mailbox-recognize'),
    path(
        'private-media/invoices/<path:path>',
        PrivateInvoiceFileView.as_view(),
        name='private-invoice-file',
    ),
]
