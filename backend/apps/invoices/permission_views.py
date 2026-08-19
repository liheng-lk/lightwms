"""Permission-hardened invoice views."""
from rest_framework import status
from rest_framework.response import Response

from core.permissions import IsItemManagerOrSuperAdmin, IsSuperAdmin
from core.role_utils import is_super_admin
from core.pagination import StandardPagination

from .filters import InvoiceFilterError, get_filtered_invoices
from .models import Invoice
from .serializers import InvoiceSerializer
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


class InvoiceListCreateView(BaseInvoiceListCreateView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        try:
            invoices = get_filtered_invoices(request.query_params)
        except InvoiceFilterError as exc:
            return Response(
                {'code': 'INVALID_FILTER', 'message': str(exc), 'details': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(invoices, request)
        if page is not None:
            return paginator.get_paginated_response(InvoiceSerializer(page, many=True).data)
        return Response(InvoiceSerializer(invoices, many=True).data, status=status.HTTP_200_OK)


class InvoiceDetailView(BaseInvoiceDetailView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get_object(self, pk):
        try:
            return Invoice.objects.select_related(
                'item', 'item__owner', 'created_by'
            ).get(pk=pk)
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
        categories = list(
            Invoice.objects.exclude(category='')
            .values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
        return Response(categories, status=status.HTTP_200_OK)


class InvoiceMonthsView(BaseInvoiceMonthsView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        months = list(
            Invoice.objects.exclude(registered_month='')
            .values_list('registered_month', flat=True)
            .distinct()
            .order_by('-registered_month')
        )
        return Response(months, status=status.HTTP_200_OK)
