"""
Serializers for inventory management.
"""
from rest_framework import serializers

from .models import Warehouse, Location, Category


class WarehouseSerializer(serializers.ModelSerializer):
    """Serializer for Warehouse model (read operations)."""
    
    class Meta:
        model = Warehouse
        fields = [
            'id',
            'code',
            'name',
            'description',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class WarehouseCreateSerializer(serializers.Serializer):
    """Serializer for creating warehouses."""
    
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_code(self, value):
        """Validate warehouse code format and uniqueness."""
        value = value.strip().upper()
        if Warehouse.objects.filter(code=value).exists():
            raise serializers.ValidationError('A warehouse with this code already exists.')
        return value


class WarehouseUpdateSerializer(serializers.Serializer):
    """Serializer for updating warehouses."""
    
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model (read operations)."""
    
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    parent_code = serializers.CharField(source='parent.code', read_only=True, allow_null=True)
    full_path = serializers.CharField(read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = Location
        fields = [
            'id',
            'warehouse',
            'warehouse_code',
            'parent',
            'parent_code',
            'code',
            'name',
            'owner',
            'owner_name',
            'is_active',
            'full_path',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class LocationCreateSerializer(serializers.Serializer):
    """Serializer for creating locations."""
    
    warehouse = serializers.IntegerField(source='warehouse_id')
    parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True)
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=100)
    owner = serializers.IntegerField(source='owner_id')
    
    def validate_code(self, value):
        """Validate location code format."""
        return value.strip().upper()
    
    def validate(self, data):
        """Validate warehouse and code uniqueness."""
        warehouse_id = data.get('warehouse_id')
        code = data.get('code')
        
        if warehouse_id and code:
            if Location.objects.filter(warehouse_id=warehouse_id, code=code).exists():
                raise serializers.ValidationError({
                    'code': 'A location with this code already exists in this warehouse.'
                })
        
        return data


class LocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating locations."""
    
    code = serializers.CharField(max_length=50, required=False)
    name = serializers.CharField(max_length=100, required=False)
    owner = serializers.IntegerField(source='owner_id', required=False)


class LocationTreeNodeSerializer(serializers.Serializer):
    """Serializer for location tree node."""
    
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    parent_id = serializers.IntegerField(allow_null=True)
    children = serializers.ListField(child=serializers.DictField(), default=list)



class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model (read operations)."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    full_path = serializers.CharField(read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id',
            'parent',
            'parent_name',
            'name',
            'is_active',
            'full_path',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class CategoryCreateSerializer(serializers.Serializer):
    """Serializer for creating categories."""
    
    parent = serializers.IntegerField(source='parent_id', required=False, allow_null=True)
    name = serializers.CharField(max_length=100)
    
    def validate_name(self, value):
        """Validate category name."""
        return value.strip()


class CategoryUpdateSerializer(serializers.Serializer):
    """Serializer for updating categories."""
    
    name = serializers.CharField(max_length=100, required=False)
    
    def validate_name(self, value):
        """Validate category name."""
        return value.strip()


class CategoryTreeNodeSerializer(serializers.Serializer):
    """Serializer for category tree node."""
    
    id = serializers.IntegerField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    parent_id = serializers.IntegerField(allow_null=True)
    children = serializers.ListField(child=serializers.DictField(), default=list)


from .models import Item, ItemImage, ItemType, ItemStatus


class ItemImageNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for ItemImage in Item responses."""
    
    original_url = serializers.SerializerMethodField()
    thumb_256_url = serializers.SerializerMethodField()
    thumb_768_url = serializers.SerializerMethodField()
    thumb_1600_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemImage
        fields = [
            'id',
            'original',
            'thumb_256',
            'thumb_768',
            'thumb_1600',
            'original_url',
            'thumb_256_url',
            'thumb_768_url',
            'thumb_1600_url',
            'is_primary',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_original_url(self, obj):
        """Get URL for original image."""
        return f'/media/{obj.original}' if obj.original else None
    
    def get_thumb_256_url(self, obj):
        """Get URL for 256px thumbnail."""
        return f'/media/{obj.thumb_256}' if obj.thumb_256 else None
    
    def get_thumb_768_url(self, obj):
        """Get URL for 768px thumbnail."""
        return f'/media/{obj.thumb_768}' if obj.thumb_768 else None
    
    def get_thumb_1600_url(self, obj):
        """Get URL for 1600px thumbnail."""
        return f'/media/{obj.thumb_1600}' if obj.thumb_1600 else None


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for Item model (read operations)."""
    
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    location_code = serializers.CharField(source='location.code', read_only=True)
    location_full_path = serializers.CharField(source='location.full_path', read_only=True)
    warehouse_code = serializers.CharField(source='location.warehouse.code', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    images = ItemImageNestedSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_borrower = serializers.SerializerMethodField()
    current_borrow_record_id = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    borrowed_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id',
            'name',
            'sku',
            'barcode',
            'category',
            'category_name',
            'unit',
            'description',
            'location',
            'location_code',
            'location_full_path',
            'warehouse_code',
            'owner',
            'owner_username',
            'type',
            'status',
            'quantity',
            'available_quantity',
            'borrowed_quantity',
            'is_active',
            'created_at',
            'updated_at',
            'images',
            'primary_image',
            'current_borrower',
            'current_borrow_record_id',
        ]
        read_only_fields = fields
    
    def get_available_quantity(self, obj):
        """Get available quantity for borrowing/taking."""
        return obj.available_quantity
    
    def get_borrowed_quantity(self, obj):
        """Get currently borrowed quantity (for reusable items)."""
        return obj.borrowed_quantity
    
    def get_current_borrower(self, obj):
        """Get current borrower username for borrowed items."""
        if obj.status != 'borrowed':
            return None
        # Import here to avoid circular imports
        from apps.operations.models import BorrowRecord
        active_borrow = BorrowRecord.objects.filter(
            item_id=obj.id,
            status='active'
        ).select_related('borrower').first()
        if active_borrow and active_borrow.borrower:
            return active_borrow.borrower.username
        return None
    
    def get_current_borrow_record_id(self, obj):
        """Get current borrow record ID for borrowed items."""
        if obj.status != 'borrowed':
            return None
        from apps.operations.models import BorrowRecord
        active_borrow = BorrowRecord.objects.filter(
            item_id=obj.id,
            status='active'
        ).first()
        return active_borrow.id if active_borrow else None
    
    def get_primary_image(self, obj):
        """Get primary image thumbnail URL for list view."""
        # Check if images are prefetched
        if hasattr(obj, '_prefetched_objects_cache') and 'images' in obj._prefetched_objects_cache:
            images = obj._prefetched_objects_cache['images']
            primary = next((img for img in images if img.is_primary), None)
            if not primary and images:
                primary = images[0]
        else:
            primary = obj.images.filter(is_primary=True).first()
            if not primary:
                primary = obj.images.first()
        
        if primary:
            return {
                'thumb_256_url': f'/media/{primary.thumb_256}' if primary.thumb_256 else None,
                'thumb_768_url': f'/media/{primary.thumb_768}' if primary.thumb_768 else None,
            }
        return None


class ItemCreateSerializer(serializers.Serializer):
    """Serializer for creating items."""
    
    name = serializers.CharField(max_length=200)
    sku = serializers.CharField(max_length=50)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category = serializers.IntegerField(source='category_id', required=False, allow_null=True)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.IntegerField(source='location_id')
    owner = serializers.IntegerField(source='owner_id', required=False, allow_null=True)
    type = serializers.ChoiceField(choices=ItemType.choices, default=ItemType.REUSABLE)
    quantity = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    
    def validate_sku(self, value):
        """Validate SKU format."""
        return value.strip().upper()
    
    def validate_barcode(self, value):
        """Validate barcode format."""
        if value:
            return value.strip()
        return None
    
    def validate(self, data):
        """Validate item data."""
        item_type = data.get('type', ItemType.REUSABLE)
        quantity = data.get('quantity')
        
        # Consumable items should have quantity
        if item_type == ItemType.CONSUMABLE and quantity is None:
            data['quantity'] = 0
        
        # Reusable items default to quantity 1 if not specified
        if item_type == ItemType.REUSABLE:
            if quantity is None:
                data['quantity'] = 1
            elif quantity < 1:
                raise serializers.ValidationError({
                    'quantity': '可重复使用物品数量至少为1'
                })
        
        return data


class ItemUpdateSerializer(serializers.Serializer):
    """Serializer for updating items."""
    
    name = serializers.CharField(max_length=200, required=False)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category = serializers.IntegerField(source='category_id', required=False, allow_null=True)
    unit = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    location = serializers.IntegerField(source='location_id', required=False)
    quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    
    def validate_barcode(self, value):
        """Validate barcode format."""
        if value:
            return value.strip()
        return None


class ItemImageSerializer(serializers.ModelSerializer):
    """Serializer for ItemImage model."""
    
    original_url = serializers.SerializerMethodField()
    thumb_256_url = serializers.SerializerMethodField()
    thumb_768_url = serializers.SerializerMethodField()
    thumb_1600_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemImage
        fields = [
            'id',
            'item',
            'original',
            'thumb_256',
            'thumb_768',
            'thumb_1600',
            'original_url',
            'thumb_256_url',
            'thumb_768_url',
            'thumb_1600_url',
            'is_primary',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_original_url(self, obj):
        """Get full URL for original image."""
        request = self.context.get('request')
        if request and obj.original:
            return request.build_absolute_uri(f'/media/{obj.original}')
        return f'/media/{obj.original}' if obj.original else None
    
    def get_thumb_256_url(self, obj):
        """Get full URL for 256px thumbnail."""
        request = self.context.get('request')
        if request and obj.thumb_256:
            return request.build_absolute_uri(f'/media/{obj.thumb_256}')
        return f'/media/{obj.thumb_256}' if obj.thumb_256 else None
    
    def get_thumb_768_url(self, obj):
        """Get full URL for 768px thumbnail."""
        request = self.context.get('request')
        if request and obj.thumb_768:
            return request.build_absolute_uri(f'/media/{obj.thumb_768}')
        return f'/media/{obj.thumb_768}' if obj.thumb_768 else None
    
    def get_thumb_1600_url(self, obj):
        """Get full URL for 1600px thumbnail."""
        request = self.context.get('request')
        if request and obj.thumb_1600:
            return request.build_absolute_uri(f'/media/{obj.thumb_1600}')
        return f'/media/{obj.thumb_1600}' if obj.thumb_1600 else None


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for image upload request."""
    
    image = serializers.ImageField(required=True)
    is_primary = serializers.BooleanField(required=False, default=False)


class BarcodeLabelSerializer(serializers.Serializer):
    """Serializer for barcode generation result."""
    
    barcode = serializers.CharField()
    label_png_base64 = serializers.CharField()


class ItemByBarcodeSerializer(serializers.ModelSerializer):
    """Serializer for item lookup by barcode (mobile scanner)."""
    
    location_full_path = serializers.CharField(source='location.full_path', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'id',
            'name',
            'sku',
            'barcode',
            'type',
            'status',
            'quantity',
            'location_full_path',
            'owner_username',
            'primary_image',
        ]
        read_only_fields = fields
    
    def get_primary_image(self, obj):
        """Get primary image thumbnail URL."""
        # Check if images are prefetched
        if hasattr(obj, '_prefetched_objects_cache') and 'images' in obj._prefetched_objects_cache:
            images = obj._prefetched_objects_cache['images']
            primary = next((img for img in images if img.is_primary), None)
            if not primary and images:
                primary = images[0]
        else:
            primary = obj.images.filter(is_primary=True).first()
            if not primary:
                primary = obj.images.first()
        
        if primary:
            return {
                'thumb_256_url': f'/media/{primary.thumb_256}' if primary.thumb_256 else None,
            }
        return None
