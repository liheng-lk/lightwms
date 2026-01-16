"""
URL configuration for invoices app.
"""
from django.urls import path

from .views import (
    InvoiceListCreateView,
    InvoiceDetailView,
    InvoiceStatusUpdateView,
    InvoiceExportView,
    InvoiceCategoriesView,
    InvoiceMonthsView,
    InvoiceBatchStatusUpdateView,
    InvoiceBatchDeleteView,
)

urlpatterns = [
    # Invoice CRUD
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list-create'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    
    # Invoice status update
    path('invoices/<int:pk>/status/', InvoiceStatusUpdateView.as_view(), name='invoice-status-update'),
    
    # Batch operations
    path('invoices/batch/status/', InvoiceBatchStatusUpdateView.as_view(), name='invoice-batch-status'),
    path('invoices/batch/delete/', InvoiceBatchDeleteView.as_view(), name='invoice-batch-delete'),
    
    # Export
    path('invoices/export/', InvoiceExportView.as_view(), name='invoice-export'),
    
    # Metadata
    path('invoices/categories/', InvoiceCategoriesView.as_view(), name='invoice-categories'),
    path('invoices/months/', InvoiceMonthsView.as_view(), name='invoice-months'),
]
