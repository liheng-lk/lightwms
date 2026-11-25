"""
Webhook models for LightWMS.

Provides a WebhookEndpoint model for configuring external notification
endpoints that receive event-driven POST requests when inventory and
operation data changes occur.
"""
from django.db import models
from django.conf import settings


class WebhookEvent(models.TextChoices):
    """Supported webhook event types."""
    ITEM_CREATED = 'item_created', '物品创建'
    ITEM_UPDATED = 'item_updated', '物品更新'
    ITEM_DELETED = 'item_deleted', '物品删除'
    BORROW_CREATED = 'borrow_created', '借用创建'
    BORROW_RETURNED = 'borrow_returned', '借用归还'
    TAKE_CREATED = 'take_created', '领用创建'
    REPLENISH_CREATED = 'replenish_created', '补货创建'


class WebhookEndpoint(models.Model):
    """
    Webhook endpoint configuration.

    Stores the URL, authentication secret, and subscribed events for
    external systems that want to receive real-time notifications.
    
    Only Super Admin can manage webhook endpoints.
    """

    # Target URL that receives POST requests
    url = models.URLField(max_length=2048)

    # HMAC secret for request signing (X-Webhook-Signature header)
    secret = models.CharField(max_length=255, blank=True, default='')

    # List of event types this endpoint subscribes to
    events = models.JSONField(
        default=list,
        help_text='List of event type strings, e.g. ["item_created", "borrow_created"]',
    )

    # Whether this endpoint is active
    is_active = models.BooleanField(default=True)

    # Optional human-readable name
    name = models.CharField(max_length=200, blank=True, default='')

    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_endpoints',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'settings_webhook_endpoint'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        active = '' if self.is_active else ' [Inactive]'
        label = self.name or self.url
        return f"{label}{active}"
