"""
Invoice service for LightWMS.

Handles invoice CRUD operations with:
- File upload and storage
- Audit logging
- Export functionality
"""
import os
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List, BinaryIO

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.invoices.models import Invoice, InvoiceStatus
from apps.inventory.models import Item
from apps.audit.models import AuditLog, AuditAction, TargetType
from apps.users.models import User
from core.exceptions import BusinessConflictError


class InvoiceService:
    """
    Service class for invoice operations.
    
    Handles:
    - Invoice CRUD operations
    - File upload and storage
    - Audit logging
    - Export functionality
    """
    
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def _get_invoice_audit_data(cls, invoice: Invoice) -> dict:
        """Extract audit-safe data from invoice."""
        return {
            'name': invoice.name,
            'amount': str(invoice.amount),
            'category': invoice.category,
            'custom_type': invoice.custom_type,
            'project': invoice.project,
            'status': invoice.status,
            'item_id': invoice.item_id,
            'registered_month': invoice.registered_month,
        }
    
    @classmethod
    def _create_audit_log(
        cls,
        action: str,
        target_id: int,
        before: Optional[dict],
        after: Optional[dict],
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> AuditLog:
        """Create an audit log entry."""
        return AuditLog.objects.create(
            action=action,
            target_type=TargetType.INVOICE,
            target_id=target_id,
            diff={'before': before, 'after': after},
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip,
            user_agent=user_agent,
        )
    
    @classmethod
    def _validate_file(cls, file: BinaryIO, filename: str) -> str:
        """
        Validate uploaded file.
        
        Args:
            file: File object
            filename: Original filename
            
        Returns:
            File extension (lowercase)
            
        Raises:
            BusinessConflictError: If file is invalid
        """
        # Check extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise BusinessConflictError(
                code='INVALID_FILE_TYPE',
                message=f'Invalid file type. Allowed types: {", ".join(cls.ALLOWED_EXTENSIONS)}',
                details={'filename': filename, 'extension': ext}
            )
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > cls.MAX_FILE_SIZE:
            raise BusinessConflictError(
                code='FILE_TOO_LARGE',
                message=f'File too large. Maximum size: {cls.MAX_FILE_SIZE // (1024*1024)}MB',
                details={'size': size, 'max_size': cls.MAX_FILE_SIZE}
            )
        
        return ext
    
    @classmethod
    def _save_file(cls, file: BinaryIO, filename: str, invoice_name: str) -> tuple:
        """
        Save uploaded file to storage.
        
        Files are stored in: /media/invoices/{year}/{month}/{uuid}{ext}
        
        Args:
            file: File object
            filename: Original filename
            invoice_name: Invoice name (used for naming the file)
            
        Returns:
            Tuple of (relative_path, original_filename)
        """
        ext = cls._validate_file(file, filename)
        
        # Generate storage path
        now = timezone.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        
        # Create directory if not exists
        dir_path = os.path.join(settings.MEDIA_ROOT, 'invoices', year, month)
        os.makedirs(dir_path, exist_ok=True)
        
        # Generate unique filename using invoice name
        safe_name = "".join(c for c in invoice_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name[:50]  # Limit length
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"{safe_name}_{unique_id}{ext}"
        
        # Save file
        file_path = os.path.join(dir_path, new_filename)
        with open(file_path, 'wb') as dest:
            for chunk in iter(lambda: file.read(8192), b''):
                dest.write(chunk)
        
        # Return relative path
        relative_path = f"invoices/{year}/{month}/{new_filename}"
        return relative_path, filename
    
    @classmethod
    def _delete_file(cls, file_path: str) -> None:
        """Delete a file from storage."""
        if file_path:
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
    
    @classmethod
    @transaction.atomic
    def create(
        cls,
        name: str,
        amount: Decimal,
        category: str,
        file: BinaryIO,
        filename: str,
        operator: User,
        custom_type: str = '',
        project: str = '',
        item_id: Optional[int] = None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Invoice:
        """
        Create a new invoice.
        
        Args:
            name: Invoice name
            amount: Invoice amount
            category: Invoice category
            file: Uploaded file object
            filename: Original filename
            operator: User creating the invoice
            custom_type: Custom type for classification
            project: Project name (optional)
            item_id: Associated item ID (optional)
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Invoice
            
        Raises:
            BusinessConflictError: If validation fails
        """
        # Validate item if provided
        item = None
        if item_id:
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                raise BusinessConflictError(
                    code='ITEM_NOT_FOUND',
                    message='Associated item not found.',
                    details={'item_id': item_id}
                )
        
        # Save file
        file_path, original_filename = cls._save_file(file, filename, name)
        
        # Get current month for registration
        registered_month = timezone.now().strftime('%Y-%m')
        
        try:
            # Create invoice
            invoice = Invoice.objects.create(
                name=name,
                amount=amount,
                category=category,
                custom_type=custom_type,
                project=project,
                file=file_path,
                original_filename=original_filename,
                status=InvoiceStatus.PENDING,
                item=item,
                registered_month=registered_month,
                created_by=operator,
            )
            
            # Create audit log
            cls._create_audit_log(
                action=AuditAction.CREATE,
                target_id=invoice.id,
                before=None,
                after=cls._get_invoice_audit_data(invoice),
                operator=operator,
                ip=ip,
                user_agent=user_agent,
            )
            
            return invoice
            
        except Exception as e:
            # Clean up file on error
            cls._delete_file(file_path)
            raise
    
    @classmethod
    @transaction.atomic
    def update(
        cls,
        invoice_id: int,
        operator: User,
        name: Optional[str] = None,
        amount: Optional[Decimal] = None,
        category: Optional[str] = None,
        custom_type: Optional[str] = None,
        project: Optional[str] = None,
        status: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> Invoice:
        """
        Update an invoice.
        
        Args:
            invoice_id: ID of invoice to update
            operator: User performing the update
            name: New name (optional)
            amount: New amount (optional)
            category: New category (optional)
            custom_type: New custom type (optional)
            project: New project name (optional)
            status: New status (optional)
            ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated Invoice
            
        Raises:
            Invoice.DoesNotExist: If invoice not found
            BusinessConflictError: If permission denied
        """
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        
        # Capture state before change
        before = cls._get_invoice_audit_data(invoice)
        
        # Update fields
        if name is not None:
            invoice.name = name
        if amount is not None:
            invoice.amount = amount
        if category is not None:
            invoice.category = category
        if custom_type is not None:
            invoice.custom_type = custom_type
        if project is not None:
            invoice.project = project
        
        # Status can be changed by any authenticated user (not read_only_user)
        if status is not None:
            invoice.status = status
        
        invoice.save()
        
        # Create audit log
        cls._create_audit_log(
            action=AuditAction.UPDATE,
            target_id=invoice.id,
            before=before,
            after=cls._get_invoice_audit_data(invoice),
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        return invoice
    
    @classmethod
    @transaction.atomic
    def delete(
        cls,
        invoice_id: int,
        operator: User,
        ip: Optional[str] = None,
        user_agent: str = ''
    ) -> None:
        """
        Delete an invoice.
        
        Args:
            invoice_id: ID of invoice to delete
            operator: User performing the deletion
            ip: Client IP address
            user_agent: Client user agent
            
        Raises:
            Invoice.DoesNotExist: If invoice not found
        """
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Capture state before deletion
        before = cls._get_invoice_audit_data(invoice)
        
        # Delete file
        cls._delete_file(invoice.file)
        
        # Create audit log before deletion
        cls._create_audit_log(
            action=AuditAction.DEACTIVATE,  # Using DEACTIVATE for deletion
            target_id=invoice.id,
            before=before,
            after=None,
            operator=operator,
            ip=ip,
            user_agent=user_agent,
        )
        
        # Delete invoice
        invoice.delete()
    
    @classmethod
    def get(cls, invoice_id: int) -> Invoice:
        """
        Get an invoice by ID.
        
        Args:
            invoice_id: ID of invoice
            
        Returns:
            Invoice instance
            
        Raises:
            Invoice.DoesNotExist: If not found
        """
        return Invoice.objects.select_related(
            'item', 'created_by'
        ).get(id=invoice_id)
    
    @classmethod
    def list(
        cls,
        category: Optional[str] = None,
        status: Optional[str] = None,
        registered_month: Optional[str] = None,
        item_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> QuerySet:
        """
        List invoices with optional filters.
        
        Args:
            category: Filter by category
            status: Filter by status
            registered_month: Filter by registered month (YYYY-MM)
            item_id: Filter by associated item
            created_by_id: Filter by creator
            search: Search in name
            
        Returns:
            QuerySet of Invoice
        """
        qs = Invoice.objects.select_related('item', 'created_by')
        
        if category:
            qs = qs.filter(category=category)
        
        if status:
            qs = qs.filter(status=status)
        
        if registered_month:
            qs = qs.filter(registered_month=registered_month)
        
        if item_id:
            qs = qs.filter(item_id=item_id)
        
        if created_by_id:
            qs = qs.filter(created_by_id=created_by_id)
        
        if search:
            qs = qs.filter(name__icontains=search)
        
        return qs.order_by('-created_at')
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """
        Get all unique invoice categories.
        
        Returns:
            List of category names
        """
        return list(
            Invoice.objects.values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
    
    @classmethod
    def get_months(cls) -> List[str]:
        """
        Get all unique registered months.
        
        Returns:
            List of months in YYYY-MM format
        """
        return list(
            Invoice.objects.values_list('registered_month', flat=True)
            .distinct()
            .order_by('-registered_month')
        )
    
    @classmethod
    def export_to_excel(
        cls,
        invoices: QuerySet,
    ) -> bytes:
        """
        Export invoices to Excel format.
        
        Args:
            invoices: QuerySet of invoices to export
            
        Returns:
            Excel file content as bytes
        """
        import io
        try:
            import openpyxl
            from openpyxl.utils import get_column_letter
        except ImportError:
            raise BusinessConflictError(
                code='EXPORT_UNAVAILABLE',
                message='Excel export is not available. Please install openpyxl.',
                details={}
            )
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '发票清单'
        
        # Headers
        headers = [
            '发票名称', '金额', '类别', '类型', '状态',
            '关联物品', '登记月份', '创建人', '创建时间'
        ]
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        # Data rows
        for row, invoice in enumerate(invoices, 2):
            ws.cell(row=row, column=1, value=invoice.name)
            ws.cell(row=row, column=2, value=float(invoice.amount))
            ws.cell(row=row, column=3, value=invoice.category)
            ws.cell(row=row, column=4, value=invoice.custom_type)
            ws.cell(row=row, column=5, value=invoice.get_status_display())
            ws.cell(row=row, column=6, value=invoice.item.name if invoice.item else '')
            ws.cell(row=row, column=7, value=invoice.registered_month)
            ws.cell(row=row, column=8, value=invoice.created_by.username)
            ws.cell(row=row, column=9, value=invoice.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()
    
    @classmethod
    def export_files_to_zip(
        cls,
        invoices: QuerySet,
    ) -> bytes:
        """
        Export invoice original files to ZIP archive.
        
        File naming format: {date}_{item_name}_{uploader}.{ext}
        
        Args:
            invoices: QuerySet of invoices to export
            
        Returns:
            ZIP file content as bytes
        """
        import io
        import zipfile
        
        output = io.BytesIO()
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
            for invoice in invoices:
                if invoice.file:
                    # Get full file path
                    file_path = os.path.join(settings.MEDIA_ROOT, invoice.file)
                    
                    if os.path.exists(file_path):
                        # Use original filename or generate one
                        ext = os.path.splitext(invoice.file)[1]
                        
                        # Format: date_itemname_uploader.ext
                        date_str = invoice.created_at.strftime('%Y%m%d')
                        
                        # Get item name or invoice name
                        item_name = invoice.item.name if invoice.item else invoice.name
                        safe_item_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '-', '_', '中', '文')).strip()
                        # Keep Chinese characters
                        safe_item_name = item_name.replace('/', '_').replace('\\', '_')[:30]
                        
                        # Get uploader name
                        uploader = invoice.created_by.username if invoice.created_by else 'unknown'
                        
                        archive_name = f"{invoice.category}/{date_str}_{safe_item_name}_{uploader}{ext}"
                        
                        # Add file to zip
                        zf.write(file_path, archive_name)
        
        output.seek(0)
        return output.read()
