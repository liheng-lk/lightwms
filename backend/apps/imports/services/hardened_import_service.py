"""Hardened inventory import service.

This compatibility layer fixes import behavior that predates reusable-item
quantity support. It also isolates each row in its own savepoint so one bad row
does not poison an allow_partial import transaction.
"""
from django.db import IntegrityError, transaction

from apps.audit.models import AuditAction, AuditLog, TargetType
from apps.inventory.models import Item, ItemStatus, ItemType
from apps.users.models import User, UserRole
from core.exceptions import BusinessConflictError

from .import_service import ImportError, ImportResult, ImportService


class HardenedImportService(ImportService):
    """Import items while preserving current owner and quantity invariants."""

    @classmethod
    def _build_user_lookup(cls):
        """Only users allowed to own inventory are valid import owners."""
        users = {}
        queryset = User.objects.filter(
            is_active=True,
            role__in=[UserRole.SUPER_ADMIN, UserRole.ITEM_MANAGER],
        )
        for user in queryset:
            users[user.username.lower()] = user
            if user.phone:
                users[user.phone.lower()] = user
        return users

    @classmethod
    def import_items(
        cls,
        file_content: bytes,
        file_name: str,
        operator,
        ip=None,
        user_agent: str = '',
        allow_partial: bool = True,
    ) -> ImportResult:
        result = ImportResult()

        cls.validate_file_size(len(file_content))

        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        if file_ext == 'csv':
            headers, rows = cls.parse_csv(file_content)
        elif file_ext in ['xlsx', 'xls']:
            headers, rows = cls.parse_xlsx(file_content)
        else:
            raise BusinessConflictError(
                code='INVALID_FILE_TYPE',
                message='File must be CSV or XLSX format.',
                details={'extension': file_ext},
            )

        cls.validate_row_count(len(rows))

        header_errors = cls.validate_headers(headers)
        if header_errors:
            result.errors.extend(header_errors)
            result.error_count = len(header_errors)
            return result

        validated_rows, validation_errors = cls.validate_rows(rows, headers)
        result.errors.extend(validation_errors)
        result.error_count = len(validation_errors)

        if not allow_partial and validation_errors:
            return result

        existing_skus = set(
            Item.objects.filter(
                sku__in=[row['sku'] for row in validated_rows]
            ).values_list('sku', flat=True)
        )

        for row_data in validated_rows:
            row_num = row_data.get('_row_num', 0)
            try:
                # Each row gets its own savepoint. IntegrityError from a duplicate
                # barcode/SKU then rolls back only this row and leaves the
                # connection usable for subsequent valid rows.
                with transaction.atomic():
                    sku = row_data['sku']
                    is_update = sku in existing_skus

                    if is_update:
                        item = Item.objects.select_for_update().get(sku=sku)
                        before = cls._get_audit_data(item)

                        # Upsert must not silently reinterpret a reusable asset
                        # as consumable (or vice versa).
                        if item.type != row_data['type']:
                            raise ValueError(
                                f'Existing item type is {item.type}; import row specifies {row_data["type"]}.'
                            )

                        item.name = row_data['name']
                        item.location = row_data['location']
                        if 'barcode' in row_data:
                            item.barcode = row_data['barcode']
                        if 'unit' in row_data:
                            item.unit = row_data['unit']
                        if 'description' in row_data:
                            item.description = row_data['description']
                        if 'category' in row_data:
                            item.category = row_data['category']
                        if 'owner' in row_data:
                            item.owner = row_data['owner']

                        if 'quantity' in row_data:
                            quantity = row_data['quantity']
                            if item.type == ItemType.REUSABLE:
                                if quantity < 1:
                                    raise ValueError('Reusable quantity must be at least 1.')
                                borrowed = item.borrowed_quantity
                                if quantity < borrowed:
                                    raise ValueError(
                                        f'Quantity {quantity} is less than currently borrowed quantity {borrowed}.'
                                    )
                                item.quantity = quantity
                                item.status = (
                                    ItemStatus.BORROWED
                                    if quantity - borrowed == 0
                                    else ItemStatus.AVAILABLE
                                )
                            else:
                                item.quantity = quantity
                                item.status = (
                                    ItemStatus.IN_STOCK
                                    if quantity > 0
                                    else ItemStatus.OUT_OF_STOCK
                                )

                        item.save()

                        after = cls._get_audit_data(item)
                        if before != after:
                            AuditLog.objects.create(
                                action=AuditAction.UPDATE,
                                target_type=TargetType.ITEM,
                                target_id=item.id,
                                diff={'before': before, 'after': after},
                                operator=operator,
                                operator_role=getattr(operator, 'role', ''),
                                ip=ip,
                                user_agent=user_agent,
                            )
                        result.update_count += 1
                    else:
                        item_type = row_data['type']
                        quantity = row_data.get('quantity')

                        if item_type == ItemType.REUSABLE:
                            if quantity is None:
                                quantity = 1
                            if quantity < 1:
                                raise ValueError('Reusable quantity must be at least 1.')
                            item_status = ItemStatus.AVAILABLE
                        else:
                            quantity = quantity if quantity is not None else 0
                            item_status = (
                                ItemStatus.IN_STOCK
                                if quantity > 0
                                else ItemStatus.OUT_OF_STOCK
                            )

                        owner = row_data.get('owner', operator)
                        if owner.role not in [UserRole.SUPER_ADMIN, UserRole.ITEM_MANAGER]:
                            raise ValueError('Inventory owner must be a super admin or item manager.')

                        item = Item.objects.create(
                            name=row_data['name'],
                            sku=sku,
                            barcode=row_data.get('barcode'),
                            category=row_data.get('category'),
                            unit=row_data.get('unit', ''),
                            description=row_data.get('description', ''),
                            location=row_data['location'],
                            owner=owner,
                            type=item_type,
                            status=item_status,
                            quantity=quantity,
                            is_active=True,
                        )

                        AuditLog.objects.create(
                            action=AuditAction.CREATE,
                            target_type=TargetType.ITEM,
                            target_id=item.id,
                            diff={'before': None, 'after': cls._get_audit_data(item)},
                            operator=operator,
                            operator_role=getattr(operator, 'role', ''),
                            ip=ip,
                            user_agent=user_agent,
                        )
                        result.create_count += 1
                        existing_skus.add(sku)

                    result.success_count += 1

            except (IntegrityError, ValueError) as exc:
                result.errors.append(
                    ImportError(
                        row=row_num,
                        field='',
                        message=f'Failed to import row: {str(exc)}',
                    )
                )
                result.error_count += 1
            except Exception as exc:
                # Preserve the original partial-import contract for unexpected
                # row-level failures while still allowing subsequent rows.
                result.errors.append(
                    ImportError(
                        row=row_num,
                        field='',
                        message=f'Failed to import row: {str(exc)}',
                    )
                )
                result.error_count += 1

        with transaction.atomic():
            AuditLog.objects.create(
                action=AuditAction.IMPORT,
                target_type=TargetType.ITEM,
                target_id=0,
                diff={
                    'file_name': file_name,
                    'total_rows': len(rows),
                    'success_count': result.success_count,
                    'create_count': result.create_count,
                    'update_count': result.update_count,
                    'error_count': result.error_count,
                },
                operator=operator,
                operator_role=getattr(operator, 'role', ''),
                ip=ip,
                user_agent=user_agent,
            )

        return result
