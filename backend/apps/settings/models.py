"""
System settings models for LightWMS.
"""
from django.db import models
from django.conf import settings


class SystemSettings(models.Model):
    """
    System-wide settings stored as key-value pairs.
    
    This is a singleton-like model where each key can only have one value.
    Used for storing system-level configurations like Logo, etc.
    """
    key = models.CharField(max_length=100, primary_key=True)
    value = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}..."
    
    # Predefined setting keys
    LOGO_URL = 'logo_url'
    LOGO_FILE = 'logo_file'  # Stores the file path for uploaded logos
