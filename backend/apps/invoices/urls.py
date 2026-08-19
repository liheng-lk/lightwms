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
]
