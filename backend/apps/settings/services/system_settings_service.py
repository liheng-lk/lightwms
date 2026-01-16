"""
System settings service for LightWMS.
"""
import os
import uuid
from typing import Optional
from django.conf import settings as django_settings
from django.core.files.uploadedfile import UploadedFile

from apps.audit.models import AuditLog, AuditAction, TargetType
from ..models import SystemSettings


class SystemSettingsService:
    """
    Service for managing system-wide settings.
    
    Provides functionality for:
    - Getting and setting system settings
    - Uploading and managing system logo
    """
    
    # Allowed logo file extensions
    ALLOWED_LOGO_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}
    # Maximum logo file size (2MB)
    MAX_LOGO_SIZE = 2 * 1024 * 1024
    # Logo storage directory
    LOGO_UPLOAD_DIR = 'system'
    
    @classmethod
    def get_setting(cls, key: str, default: str = '') -> str:
        """
        Get a system setting value.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        try:
            setting = SystemSettings.objects.get(key=key)
            return setting.value
        except SystemSettings.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(
        cls,
        key: str,
        value: str,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> SystemSettings:
        """
        Set a system setting value.
        
        Args:
            key: Setting key
            value: Setting value
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated SystemSettings instance
        """
        setting, created = SystemSettings.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'updated_by': operator,
            }
        )
        
        # Create audit log
        AuditLog.objects.create(
            action=AuditAction.UPDATE if not created else AuditAction.CREATE,
            target_type=TargetType.SYSTEM,
            target_id=0,  # System settings don't have a numeric ID
            diff={
                'key': key,
                'value': value[:100] if len(value) > 100 else value,  # Truncate for audit
            },
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
        
        return setting
    
    @classmethod
    def get_logo_url(cls) -> Optional[str]:
        """
        Get the system logo URL.
        
        Returns:
            Logo URL or None if not set
        """
        # First check for uploaded file
        logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        if logo_file:
            return f'/media/{logo_file}'
        
        # Then check for URL
        logo_url = cls.get_setting(SystemSettings.LOGO_URL)
        if logo_url:
            return logo_url
        
        return None
    
    @classmethod
    def set_logo_url(
        cls,
        url: str,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> None:
        """
        Set the system logo URL.
        
        Args:
            url: Logo URL
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
        """
        # Clear any uploaded file setting
        cls.set_setting(SystemSettings.LOGO_FILE, '', operator, ip, user_agent)
        # Set the URL
        cls.set_setting(SystemSettings.LOGO_URL, url, operator, ip, user_agent)
    
    @classmethod
    def upload_logo(
        cls,
        file: UploadedFile,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> str:
        """
        Upload a logo file.
        
        Args:
            file: Uploaded file
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            URL path to the uploaded logo
            
        Raises:
            ValueError: If file is invalid
        """
        # Validate file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in cls.ALLOWED_LOGO_EXTENSIONS:
            raise ValueError(f'不支持的文件格式。支持的格式: {", ".join(cls.ALLOWED_LOGO_EXTENSIONS)}')
        
        # Validate file size
        if file.size > cls.MAX_LOGO_SIZE:
            raise ValueError(f'文件过大。最大允许 {cls.MAX_LOGO_SIZE // 1024 // 1024}MB')
        
        # Generate unique filename
        filename = f'logo_{uuid.uuid4().hex[:8]}{ext}'
        relative_path = os.path.join(cls.LOGO_UPLOAD_DIR, filename)
        full_path = os.path.join(django_settings.MEDIA_ROOT, relative_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Delete old logo file if exists
        old_logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        if old_logo_file:
            old_path = os.path.join(django_settings.MEDIA_ROOT, old_logo_file)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass  # Ignore deletion errors
        
        # Save new file
        with open(full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Update settings
        cls.set_setting(SystemSettings.LOGO_FILE, relative_path, operator, ip, user_agent)
        cls.set_setting(SystemSettings.LOGO_URL, '', operator, ip, user_agent)
        
        return f'/media/{relative_path}'
    
    @classmethod
    def clear_logo(
        cls,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> None:
        """
        Clear the system logo (restore to default).
        
        Args:
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
        """
        # Delete logo file if exists
        logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        if logo_file:
            full_path = os.path.join(django_settings.MEDIA_ROOT, logo_file)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass
        
        # Clear settings
        cls.set_setting(SystemSettings.LOGO_FILE, '', operator, ip, user_agent)
        cls.set_setting(SystemSettings.LOGO_URL, '', operator, ip, user_agent)
    
    @classmethod
    def get_all_settings(cls) -> dict:
        """
        Get all system settings as a dictionary.
        
        Returns:
            Dictionary of all settings
        """
        return {
            'logo_url': cls.get_logo_url(),
        }
