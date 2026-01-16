"""
Image service for LightWMS.

Handles image upload, processing, and deletion with audit logging.
Uses pyvips for image processing (EXIF correction, WebP conversion, thumbnail generation).

Storage path: /media/items/{item_id}/{image_id}/
"""
import os
import shutil
import uuid
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile

from apps.inventory.models import Item, ItemImage
from apps.audit.models import AuditLog, AuditAction, TargetType
from core.exceptions import BusinessConflictError


@dataclass
class ImageUploadResult:
    """Result of image upload operation."""
    image: ItemImage
    original_url: str
    thumb_256_url: str
    thumb_768_url: str
    thumb_1600_url: str


class ImageService:
    """
    Service class for image operations.
    
    All operations that modify data create audit log entries.
    Images are stored in WebP format with multiple thumbnail sizes.
    
    Image processing:
    - Original: Max 2000px dimension, WebP format
    - Thumbnails: 256px, 768px, 1600px (max dimension, aspect ratio preserved)
    - EXIF orientation is auto-corrected
    - Quality: 85 for all WebP outputs
    
    Storage structure:
    /media/items/{item_id}/{image_id}/
        ├── original.webp
        ├── 256.webp
        ├── 768.webp
        └── 1600.webp
    """
    
    # Image processing settings
    MAX_ORIGINAL_DIMENSION = 2000
    THUMBNAIL_SIZES = [256, 768, 1600]
    WEBP_QUALITY = 85
    
    # Allowed image formats
    ALLOWED_CONTENT_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
        'image/tiff',
    ]
    
    # Max file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    @classmethod
    def _get_audit_data(cls, image: ItemImage) -> dict:
        """Extract audit-safe data from image."""
        return {
            'item_id': image.item_id,
            'original': image.original,
            'thumb_256': image.thumb_256,
            'thumb_768': image.thumb_768,
            'thumb_1600': image.thumb_1600,
            'is_primary': image.is_primary,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        image: ItemImage,
        before: Optional[dict],
        after: Optional[dict],
        operator,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry for image operations."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.ITEM_IMAGE,
            target_id=image.id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    def _validate_file(cls, file: UploadedFile) -> None:
        """
        Validate uploaded file.
        
        Raises:
            BusinessConflictError: If file is invalid
        """
        # Check file size
        if file.size > cls.MAX_FILE_SIZE:
            raise BusinessConflictError(
                code='FILE_TOO_LARGE',
                message=f'File size exceeds maximum allowed ({cls.MAX_FILE_SIZE // (1024*1024)}MB).',
                details={'max_size': cls.MAX_FILE_SIZE, 'actual_size': file.size}
            )
        
        # Check content type
        content_type = file.content_type
        if content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise BusinessConflictError(
                code='INVALID_FILE_TYPE',
                message='Invalid image format. Allowed formats: JPEG, PNG, GIF, WebP, BMP, TIFF.',
                details={'content_type': content_type}
            )
    
    @classmethod
    def _get_storage_path(cls, item_id: int, image_id: int) -> str:
        """Get the storage directory path for an image."""
        return os.path.join('items', str(item_id), str(image_id))
    
    @classmethod
    def _get_full_storage_path(cls, item_id: int, image_id: int) -> str:
        """Get the full filesystem path for image storage."""
        return os.path.join(settings.MEDIA_ROOT, cls._get_storage_path(item_id, image_id))
    
    @classmethod
    def _process_image(cls, file: UploadedFile, storage_dir: str) -> dict:
        """
        Process uploaded image using pyvips.
        
        - Auto-rotate based on EXIF orientation
        - Convert to WebP format
        - Resize original to max 2000px
        - Generate thumbnails at 256px, 768px, 1600px
        
        Args:
            file: Uploaded file
            storage_dir: Directory to save processed images
            
        Returns:
            Dict with paths to all generated images
        """
        try:
            import pyvips
        except ImportError:
            # Fallback if pyvips is not available
            return cls._process_image_fallback(file, storage_dir)
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Read image from uploaded file
        # pyvips can read from buffer
        file.seek(0)
        image_data = file.read()
        
        # Load image with random access (not sequential) to handle all JPEG types
        # Using access='random' allows pyvips to handle progressive/interlaced JPEGs
        try:
            image = pyvips.Image.new_from_buffer(image_data, '', access='random')
        except pyvips.error.Error:
            # If random access fails, try without access parameter
            image = pyvips.Image.new_from_buffer(image_data, '')
        
        # Auto-rotate based on EXIF orientation
        image = image.autorot()
        
        # Get dimensions
        width = image.width
        height = image.height
        
        # Calculate scale for original (max 2000px)
        max_dim = max(width, height)
        if max_dim > cls.MAX_ORIGINAL_DIMENSION:
            scale = cls.MAX_ORIGINAL_DIMENSION / max_dim
            image = image.resize(scale, kernel='lanczos3')
        
        # Save original as WebP
        original_path = os.path.join(storage_dir, 'original.webp')
        image.webpsave(original_path, Q=cls.WEBP_QUALITY)
        
        # Generate thumbnails
        paths = {'original': original_path}
        
        for size in cls.THUMBNAIL_SIZES:
            thumb_path = os.path.join(storage_dir, f'{size}.webp')
            
            # Calculate scale for thumbnail
            current_max = max(image.width, image.height)
            if current_max > size:
                scale = size / current_max
                thumb = image.resize(scale, kernel='lanczos3')
            else:
                thumb = image
            
            thumb.webpsave(thumb_path, Q=cls.WEBP_QUALITY)
            paths[f'thumb_{size}'] = thumb_path
        
        return paths
    
    @classmethod
    def _process_image_fallback(cls, file: UploadedFile, storage_dir: str) -> dict:
        """
        Fallback image processing using PIL if pyvips is not available.
        
        Note: This is a simplified fallback that may not handle all EXIF cases.
        """
        try:
            from PIL import Image, ExifTags
        except ImportError:
            raise BusinessConflictError(
                code='IMAGE_PROCESSING_ERROR',
                message='Image processing library not available.',
                details={}
            )
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Read image
        file.seek(0)
        image = Image.open(file)
        
        # Handle EXIF orientation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = image._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    image = image.rotate(180, expand=True)
                elif orientation_value == 6:
                    image = image.rotate(270, expand=True)
                elif orientation_value == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass
        
        # Convert to RGB if necessary (for WebP compatibility)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize original if needed
        width, height = image.size
        max_dim = max(width, height)
        if max_dim > cls.MAX_ORIGINAL_DIMENSION:
            scale = cls.MAX_ORIGINAL_DIMENSION / max_dim
            new_size = (int(width * scale), int(height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save original
        original_path = os.path.join(storage_dir, 'original.webp')
        image.save(original_path, 'WEBP', quality=cls.WEBP_QUALITY)
        
        # Generate thumbnails
        paths = {'original': original_path}
        
        for size in cls.THUMBNAIL_SIZES:
            thumb_path = os.path.join(storage_dir, f'{size}.webp')
            
            current_max = max(image.size)
            if current_max > size:
                scale = size / current_max
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                thumb = image.resize(new_size, Image.Resampling.LANCZOS)
            else:
                thumb = image.copy()
            
            thumb.save(thumb_path, 'WEBP', quality=cls.WEBP_QUALITY)
            paths[f'thumb_{size}'] = thumb_path
        
        return paths

    
    @classmethod
    def _delete_image_files(cls, image: ItemImage) -> None:
        """
        Delete all files associated with an image.
        
        Args:
            image: ItemImage instance
        """
        storage_dir = cls._get_full_storage_path(image.item_id, image.id)
        
        if os.path.exists(storage_dir):
            shutil.rmtree(storage_dir)
    
    @classmethod
    def _reassign_primary(cls, item_id: int, exclude_image_id: Optional[int] = None) -> Optional[ItemImage]:
        """
        Reassign primary image to the most recently uploaded image.
        
        Called when the current primary image is deleted.
        
        Args:
            item_id: Item ID
            exclude_image_id: Image ID to exclude (being deleted)
            
        Returns:
            New primary image or None if no images remain
        """
        # Find the most recently uploaded image
        queryset = ItemImage.objects.filter(item_id=item_id)
        if exclude_image_id:
            queryset = queryset.exclude(id=exclude_image_id)
        
        new_primary = queryset.order_by('-created_at').first()
        
        if new_primary:
            new_primary.is_primary = True
            new_primary.save(update_fields=['is_primary'])
        
        return new_primary
    
    @classmethod
    @transaction.atomic
    def upload(
        cls,
        item_id: int,
        file: UploadedFile,
        is_primary: bool = False,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> ImageUploadResult:
        """
        Upload and process an image for an item.
        
        Args:
            item_id: ID of the item
            file: Uploaded image file
            is_primary: Whether this should be the primary image
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            ImageUploadResult with image details and URLs
            
        Raises:
            Item.DoesNotExist: If item not found
            BusinessConflictError: If file is invalid or item is inactive
        """
        # Get and validate item
        item = Item.objects.select_for_update().get(id=item_id)
        
        if not item.is_active:
            raise BusinessConflictError(
                code='RESOURCE_INACTIVE',
                message='Cannot upload images to inactive items.',
                details={'item_id': item_id}
            )
        
        # Validate file
        cls._validate_file(file)
        
        # Create image record first to get ID
        image = ItemImage.objects.create(
            item=item,
            original='',  # Will be updated after processing
            thumb_256='',
            thumb_768='',
            thumb_1600='',
            is_primary=False,  # Will be set after processing
        )
        
        try:
            # Get storage path
            storage_dir = cls._get_full_storage_path(item_id, image.id)
            relative_path = cls._get_storage_path(item_id, image.id)
            
            # Process image
            paths = cls._process_image(file, storage_dir)
            
            # Update image record with paths
            image.original = os.path.join(relative_path, 'original.webp')
            image.thumb_256 = os.path.join(relative_path, '256.webp')
            image.thumb_768 = os.path.join(relative_path, '768.webp')
            image.thumb_1600 = os.path.join(relative_path, '1600.webp')
            
            # Handle primary image logic
            if is_primary:
                # Unset current primary
                ItemImage.objects.filter(item_id=item_id, is_primary=True).update(is_primary=False)
                image.is_primary = True
            else:
                # If this is the first image, make it primary
                if not ItemImage.objects.filter(item_id=item_id, is_primary=True).exclude(id=image.id).exists():
                    image.is_primary = True
            
            image.save()
            
        except Exception as e:
            # Clean up on failure
            image.delete()
            storage_dir = cls._get_full_storage_path(item_id, image.id)
            if os.path.exists(storage_dir):
                shutil.rmtree(storage_dir)
            raise
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.CREATE,
            image=image,
            before=None,
            after=cls._get_audit_data(image),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Build URLs
        media_url = settings.MEDIA_URL
        
        return ImageUploadResult(
            image=image,
            original_url=f"{media_url}{image.original}",
            thumb_256_url=f"{media_url}{image.thumb_256}",
            thumb_768_url=f"{media_url}{image.thumb_768}",
            thumb_1600_url=f"{media_url}{image.thumb_1600}",
        )
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        image_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> None:
        """
        Delete an image and all associated files.
        
        If the deleted image was primary and other images exist,
        the most recently uploaded image becomes the new primary.
        
        Args:
            image_id: ID of the image to delete
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Raises:
            ItemImage.DoesNotExist: If image not found
        """
        image = ItemImage.objects.select_for_update().get(id=image_id)
        item_id = image.item_id
        was_primary = image.is_primary
        
        # Store audit data before deletion
        before_data = cls._get_audit_data(image)
        
        # Delete files
        cls._delete_image_files(image)
        
        # Delete record
        image_id_for_audit = image.id
        image.delete()
        
        # Reassign primary if needed
        if was_primary:
            cls._reassign_primary(item_id)
        
        # Create audit log (using a temporary object for the log)
        AuditLog.objects.create(
            action=AuditAction.DEACTIVATE,  # Using DEACTIVATE for deletion
            target_type=TargetType.ITEM_IMAGE,
            target_id=image_id_for_audit,
            diff={'before': before_data, 'after': None},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    @transaction.atomic
    def set_primary(
        cls,
        image_id: int,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> ItemImage:
        """
        Set an image as the primary image for its item.
        
        Args:
            image_id: ID of the image to set as primary
            operator: User performing the operation
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated ItemImage instance
            
        Raises:
            ItemImage.DoesNotExist: If image not found
        """
        image = ItemImage.objects.select_for_update().get(id=image_id)
        
        if image.is_primary:
            # Already primary, no-op
            return image
        
        before_data = cls._get_audit_data(image)
        
        # Unset current primary
        ItemImage.objects.filter(item_id=image.item_id, is_primary=True).update(is_primary=False)
        
        # Set new primary
        image.is_primary = True
        image.save(update_fields=['is_primary'])
        
        after_data = cls._get_audit_data(image)
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.UPDATE,
            image=image,
            before=before_data,
            after=after_data,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return image
    
    @classmethod
    def get_by_id(cls, image_id: int) -> ItemImage:
        """
        Get an image by ID.
        
        Args:
            image_id: ID of the image
            
        Returns:
            ItemImage instance
            
        Raises:
            ItemImage.DoesNotExist: If not found
        """
        return ItemImage.objects.select_related('item').get(id=image_id)
    
    @classmethod
    def list_by_item(cls, item_id: int) -> list:
        """
        Get all images for an item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            List of ItemImage instances ordered by created_at desc
        """
        return list(ItemImage.objects.filter(item_id=item_id).order_by('-created_at'))
