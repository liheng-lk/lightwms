"""Permission-hardened invoice views."""
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from apps.inventory.models import Item
from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin
from core.role_utils import is_super_admin, is_item_manager
from core.pagination import StandardPagination

from .models import Invoice
from .serializers import InvoiceSerializer
from .services import InvoiceService
from .views import (
    InvoiceListCreateView as BaseInvoiceListCreateView,
    InvoiceDetailView as BaseInvoiceDetailView,
    InvoiceStatusUpdateView as BaseInvoiceStatusUpdateView,
    InvoiceExportView,
    InvoiceCategoriesView as BaseInvoiceCategoriesView,
    InvoiceMonthsView as BaseInvoiceMonthsView,
    InvoiceBatchStatusUpdateView as BaseInvoiceBatchStatusUpdateView,
    InvoiceBatchDeleteView as BaseInvoiceBatchDeleteView,
)


def _manager_invoice_scope(user):
    """Invoices created by the manager or attached to one of their items."""
    return Q(created_by_id=user.id) | Q(item__owner_id=user.id)


class InvoiceListCreateView(BaseInvoiceListCreateView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        month = request.query_params.get('month')
        item_id = request.query_params.get('item')
        search = request.query_params.get('search')

        invoices = InvoiceService.list(
            category=category,
            status=status_filter,
            registered_month=month,
            item_id=int(item_id) if item_id else None,
            search=search,
        )
        if is_item_manager(request.user):
            invoices = invoices.filter(_manager_invoice_scope(request.user)).distinct()

        paginator = StandardPagination()
        page = paginator.paginate_queryset(invoices, request)
        if page is not None:
            return paginator.get_paginated_response(InvoiceSerializer(page, many=True).data)
        return Response(InvoiceSerializer(invoices, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        item_id = request.data.get('item_id')
        if item_id and is_item_manager(request.user):
            try:
                item = Item.objects.get(pk=int(item_id))
            except (Item.DoesNotExist, TypeError, ValueError):
                return Response(
                    {'code': 'ITEM_NOT_FOUND', 'message': 'Associated item not found.', 'details': None},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if item.owner_id != request.user.id:
                return Response(
                    {'code': 'PERMISSION_DENIED', 'message': 'Permission denied.', 'details': None},
                    status=status.HTTP_403_FORBIDDEN,
                )
        return super().post(request)


class InvoiceDetailView(BaseInvoiceDetailView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk):
        qs = Invoice.objects.select_related('item', 'item__owner', 'created_by')
        if is_item_manager(self.request.user):
            qs = qs.filter(_manager_invoice_scope(self.request.user))
        try:
            return qs.get(pk=pk)
        except Invoice.DoesNotExist:
            return None

    def patch(self, request, pk):
        # Reimbursement status is an approval decision. Item managers may edit
        # invoice metadata but must never bypass the dedicated super-admin
        # status endpoint by sending status through the generic PATCH route.
        if 'status' in request.data and not is_super_admin(request.user):
            return Response(
                {
                    'code': 'PERMISSION_DENIED',
                    'message': 'Only Super Admin can change reimbursement status.',
                    'details': None,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().patch(request, pk)


class InvoiceStatusUpdateView(BaseInvoiceStatusUpdateView):
    """Reimbursement state is a system-level approval action."""
    permission_classes = [IsSuperAdmin]


class InvoiceBatchStatusUpdateView(BaseInvoiceBatchStatusUpdateView):
    permission_classes = [IsSuperAdmin]


class InvoiceBatchDeleteView(BaseInvoiceBatchDeleteView):
    """Bulk destructive operations stay Super Admin only."""
    permission_classes = [IsSuperAdmin]


class InvoiceCategoriesView(BaseInvoiceCategoriesView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        qs = Invoice.objects.all()
        if is_item_manager(request.user):
            qs = qs.filter(_manager_invoice_scope(request.user)).distinct()
        categories = list(
            qs.exclude(category='')
            .values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
        return Response(categories, status=status.HTTP_200_OK)


class InvoiceMonthsView(BaseInvoiceMonthsView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        qs = Invoice.objects.all()
        if is_item_manager(request.user):
            qs = qs.filter(_manager_invoice_scope(request.user)).distinct()
        months = list(
            qs.exclude(registered_month='')
            .values_list('registered_month', flat=True)
            .distinct()
            .order_by('-registered_month')
        )
        return Response(months, status=status.HTTP_200_OK)
