"""
Invoice models for LightWMS.

This module contains models for:
- Invoice: Purchase invoices that can be associated with items or standalone
"""
from django.db import models
from django.conf import settings


class InvoiceStatus(models.TextChoices):
    """Invoice reimbursement status enumeration."""
    PENDING = 'pending', '未报销'
    REIMBURSED = 'reimbursed', '已报销'
    REJECTED = 'rejected', '无法报销'


class Invoice(models.Model):
    """
    Invoice model representing a purchase invoice.
    
    Invoices can be:
    - Associated with an item (created during item creation)
    - Standalone (created independently for non-item purchases)
    
    Features:
    - Multiple file formats supported (PDF, JPG, PNG, JPEG)
    - Reimbursement status tracking
    - Monthly grouping via registered_month
    - Category and custom type classification
    - Optional project field for project-based tracking
    
    Requirements: 23.1, 23.4, 24.2
    """
    
    # Invoice name (auto-set to item name if associated with item)
    name = models.CharField(max_length=200)
    
    # Invoice amount
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Category for classification
    category = models.CharField(max_length=100)
    
    # Custom type for further classification
    custom_type = models.CharField(max_length=100, blank=True, default='')
    
    # Project name (optional)
    project = models.CharField(max_length=200, blank=True, default='')
    
    # File path (stored in /media/invoices/{year}/{month}/)
    file = models.CharField(max_length=500)
    
    # Original file name
    original_filename = models.CharField(max_length=255)
    
    # Reimbursement status
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING
    )
    
    # Associated item (optional - null for standalone invoices)
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    # Registration month for grouping (format: YYYY-MM)
    registered_month = models.CharField(max_length=7)
    
    # Creator reference
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_invoices'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices_invoice'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['registered_month', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['item', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - ¥{self.amount} ({self.get_status_display()})"
    
    @property
    def is_pending(self) -> bool:
        """Check if invoice is pending reimbursement."""
        return self.status == InvoiceStatus.PENDING
    
    @property
    def is_reimbursed(self) -> bool:
        """Check if invoice has been reimbursed."""
        return self.status == InvoiceStatus.REIMBURSED
    
    @property
    def is_rejected(self) -> bool:
        """Check if invoice reimbursement was rejected."""
        return self.status == InvoiceStatus.REJECTED
    
    @property
    def item_name(self) -> str:
        """Get associated item name if exists."""
        return self.item.name if self.item else ''
