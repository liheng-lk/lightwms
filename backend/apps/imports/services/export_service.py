"""
Export service for LightWMS.

Handles exporting items and records to CSV/XLSX format.
"""
import csv
import io
from typing import List, Optional

from django.db.models import QuerySet

from apps.inventory.models import Item
from apps.operations.models import BorrowRecord, TakeRecord, ReplenishRecord
from apps.audit.models import AuditLog, AuditAction, TargetType
from core.exceptions import BusinessConflictError


class ExportService:
    """
    Service for exporting data to CSV/XLSX files.
    
    Features:
    - Export items with filters
    - Export borrow/take/replenish records
    - Row limit (50000)
    - Support for CSV and XLSX formats
    """
    
    # Limits
    MAX_ROWS = 50000
    
    # Export field definitions
    ITEM_FIELDS = [
        ('id', 'ID'),
        ('name', 'Name'),
        ('sku', 'SKU'),
        ('barcode', 'Barcode'),
        ('type', 'Type'),
        ('status', 'Status'),
        ('quantity', 'Quantity'),
        ('unit', 'Unit'),
        ('description', 'Description'),
        ('category__name', 'Category'),
        ('location__warehouse__code', 'Warehouse Code'),
        ('location__code', 'Location Code'),
        ('owner__username', 'Owner'),
        ('is_active', 'Active'),
        ('created_at', 'Created At'),
        ('updated_at', 'Updated At'),
    ]
    
    BORROW_RECORD_FIELDS = [
        ('id', 'ID'),
        ('item__sku', 'Item SKU'),
        ('item__name', 'Item Name'),
        ('borrower__username', 'Borrower'),
        ('borrower__phone', 'Borrower Phone'),
        ('borrower__department', 'Borrower Department'),
        ('operator__username', 'Operator'),
        ('expected_return_date', 'Expected Return Date'),
        ('actual_return_datetime', 'Actual Return Date'),
        ('status', 'Status'),
        ('notes', 'Notes'),
        ('return_notes', 'Return Notes'),
        ('condition', 'Condition'),
        ('created_at', 'Created At'),
    ]
    
    TAKE_RECORD_FIELDS = [
        ('id', 'ID'),
        ('item__sku', 'Item SKU'),
        ('item__name', 'Item Name'),
        ('taker__username', 'Taker'),
        ('taker__phone', 'Taker Phone'),
        ('taker__department', 'Taker Department'),
        ('operator__username', 'Operator'),
        ('quantity', 'Quantity'),
        ('notes', 'Notes'),
        ('created_at', 'Created At'),
    ]
    
    REPLENISH_RECORD_FIELDS = [
        ('id', 'ID'),
        ('item__sku', 'Item SKU'),
        ('item__name', 'Item Name'),
        ('operator__username', 'Operator'),
        ('quantity', 'Quantity'),
        ('notes', 'Notes'),
        ('created_at', 'Created At'),
    ]
    
    @classmethod
    def validate_row_count(cls, count: int) -> None:
        """
        Validate export row count is within limits.
        
        Args:
            count: Number of rows to export
            
        Raises:
            BusinessConflictError: If too many rows
        """
        if count > cls.MAX_ROWS:
            raise BusinessConflictError(
                code='ROW_LIMIT_EXCEEDED',
                message=f'Export row count exceeds maximum of {cls.MAX_ROWS}.',
                details={'max_rows': cls.MAX_ROWS, 'actual_rows': count}
            )
    
    @classmethod
    def _get_nested_attr(cls, obj, attr_path: str):
        """
        Get nested attribute value using dot notation.
        
        Args:
            obj: Object to get attribute from
            attr_path: Attribute path like 'location__warehouse__code'
            
        Returns:
            Attribute value or empty string
        """
        parts = attr_path.split('__')
        value = obj
        for part in parts:
            if value is None:
                return ''
            value = getattr(value, part, None)
        return value if value is not None else ''
    
    @classmethod
    def _format_value(cls, value) -> str:
        """
        Format value for export.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string
        """
        if value is None:
            return ''
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)
    
    @classmethod
    def export_items_csv(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export items to CSV format.
        
        Args:
            queryset: QuerySet of items to export
            operator: User performing the export
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            CSV file content as bytes
        """
        # Validate row count
        count = queryset.count()
        cls.validate_row_count(count)
        
        # Optimize queryset
        queryset = queryset.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [label for _, label in cls.ITEM_FIELDS]
        writer.writerow(headers)
        
        # Write data rows
        for item in queryset:
            row = []
            for field, _ in cls.ITEM_FIELDS:
                value = cls._get_nested_attr(item, field)
                row.append(cls._format_value(value))
            writer.writerow(row)
        
        # Create audit log
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.ITEM,
                target_id=0,
                diff={'format': 'csv', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        return output.getvalue().encode('utf-8-sig')

    @classmethod
    def export_items_xlsx(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export items to XLSX format.
        
        Args:
            queryset: QuerySet of items to export
            operator: User performing the export
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            XLSX file content as bytes
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        
        # Validate row count
        count = queryset.count()
        cls.validate_row_count(count)
        
        # Optimize queryset
        queryset = queryset.select_related(
            'category', 'location', 'location__warehouse', 'owner'
        )
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'Items'
        
        # Write headers with styling
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        headers = [label for _, label in cls.ITEM_FIELDS]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        # Write data rows
        for row_num, item in enumerate(queryset, start=2):
            for col, (field, _) in enumerate(cls.ITEM_FIELDS, start=1):
                value = cls._get_nested_attr(item, field)
                ws.cell(row=row_num, column=col, value=cls._format_value(value))
        
        # Adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[chr(64 + col) if col <= 26 else 'A' + chr(64 + col - 26)].width = 15
        
        # Create audit log
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.ITEM,
                target_id=0,
                diff={'format': 'xlsx', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
    
    @classmethod
    def export_borrow_records_csv(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export borrow records to CSV format.
        
        Args:
            queryset: QuerySet of borrow records to export
            operator: User performing the export
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            CSV file content as bytes
        """
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related(
            'item', 'borrower', 'operator'
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [label for _, label in cls.BORROW_RECORD_FIELDS]
        writer.writerow(headers)
        
        for record in queryset:
            row = []
            for field, _ in cls.BORROW_RECORD_FIELDS:
                value = cls._get_nested_attr(record, field)
                row.append(cls._format_value(value))
            writer.writerow(row)
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.BORROW_RECORD,
                target_id=0,
                diff={'format': 'csv', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        return output.getvalue().encode('utf-8-sig')
    
    @classmethod
    def export_borrow_records_xlsx(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export borrow records to XLSX format.
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related('item', 'borrower', 'operator')
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'Borrow Records'
        
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        headers = [label for _, label in cls.BORROW_RECORD_FIELDS]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for row_num, record in enumerate(queryset, start=2):
            for col, (field, _) in enumerate(cls.BORROW_RECORD_FIELDS, start=1):
                value = cls._get_nested_attr(record, field)
                ws.cell(row=row_num, column=col, value=cls._format_value(value))
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.BORROW_RECORD,
                target_id=0,
                diff={'format': 'xlsx', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
    
    @classmethod
    def export_take_records_csv(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export take records to CSV format.
        """
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related('item', 'taker', 'operator')
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [label for _, label in cls.TAKE_RECORD_FIELDS]
        writer.writerow(headers)
        
        for record in queryset:
            row = []
            for field, _ in cls.TAKE_RECORD_FIELDS:
                value = cls._get_nested_attr(record, field)
                row.append(cls._format_value(value))
            writer.writerow(row)
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.TAKE_RECORD,
                target_id=0,
                diff={'format': 'csv', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        return output.getvalue().encode('utf-8-sig')
    
    @classmethod
    def export_take_records_xlsx(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export take records to XLSX format.
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related('item', 'taker', 'operator')
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'Take Records'
        
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        headers = [label for _, label in cls.TAKE_RECORD_FIELDS]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for row_num, record in enumerate(queryset, start=2):
            for col, (field, _) in enumerate(cls.TAKE_RECORD_FIELDS, start=1):
                value = cls._get_nested_attr(record, field)
                ws.cell(row=row_num, column=col, value=cls._format_value(value))
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.TAKE_RECORD,
                target_id=0,
                diff={'format': 'xlsx', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
    
    @classmethod
    def export_replenish_records_csv(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export replenish records to CSV format.
        """
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related('item', 'operator')
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [label for _, label in cls.REPLENISH_RECORD_FIELDS]
        writer.writerow(headers)
        
        for record in queryset:
            row = []
            for field, _ in cls.REPLENISH_RECORD_FIELDS:
                value = cls._get_nested_attr(record, field)
                row.append(cls._format_value(value))
            writer.writerow(row)
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.REPLENISH_RECORD,
                target_id=0,
                diff={'format': 'csv', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        return output.getvalue().encode('utf-8-sig')
    
    @classmethod
    def export_replenish_records_xlsx(
        cls,
        queryset: QuerySet,
        operator=None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> bytes:
        """
        Export replenish records to XLSX format.
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        
        count = queryset.count()
        cls.validate_row_count(count)
        
        queryset = queryset.select_related('item', 'operator')
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'Replenish Records'
        
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        headers = [label for _, label in cls.REPLENISH_RECORD_FIELDS]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        for row_num, record in enumerate(queryset, start=2):
            for col, (field, _) in enumerate(cls.REPLENISH_RECORD_FIELDS, start=1):
                value = cls._get_nested_attr(record, field)
                ws.cell(row=row_num, column=col, value=cls._format_value(value))
        
        if operator:
            AuditLog.objects.create(
                action=AuditAction.EXPORT,
                target_type=TargetType.REPLENISH_RECORD,
                target_id=0,
                diff={'format': 'xlsx', 'row_count': count},
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
