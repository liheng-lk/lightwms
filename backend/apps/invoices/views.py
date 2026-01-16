"""
Views for invoice management.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsSuperAdmin
from core.pagination import StandardPagination
from core.exceptions import BusinessConflictError

from .models import Invoice
from .serializers import (
    InvoiceSerializer,
    InvoiceCreateSerializer,
    InvoiceUpdateSerializer,
    InvoiceStatusUpdateSerializer,
)
from .services import InvoiceService


class InvoiceListCreateView(APIView):
    """List and create invoices."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='category', description='Filter by category', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status (pending/reimbursed/rejected)', required=False, type=str),
            OpenApiParameter(name='month', description='Filter by registered month (YYYY-MM)', required=False, type=str),
            OpenApiParameter(name='item', description='Filter by item ID', required=False, type=int),
            OpenApiParameter(name='search', description='Search in name', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Results per page', required=False, type=int),
        ],
        responses={200: InvoiceSerializer(many=True)},
        tags=['Invoices'],
        summary='List invoices',
        description='List invoices with optional filters.',
    )
    def get(self, request):
        # Parse filters
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
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(invoices, request)
        if page is not None:
            serializer = InvoiceSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'Invoice name'},
                    'amount': {'type': 'number', 'description': 'Invoice amount'},
                    'category': {'type': 'string', 'description': 'Invoice category'},
                    'custom_type': {'type': 'string', 'description': 'Custom type (optional)'},
                    'item_id': {'type': 'integer', 'description': 'Associated item ID (optional)'},
                    'file': {'type': 'string', 'format': 'binary', 'description': 'Invoice file (PDF, JPG, PNG)'},
                },
                'required': ['name', 'amount', 'category', 'file'],
            }
        },
        responses={
            201: InvoiceSerializer,
            400: OpenApiResponse(description='Validation error'),
            409: OpenApiResponse(description='Business conflict'),
        },
        tags=['Invoices'],
        summary='Create invoice',
        description='Create a new invoice with file upload.',
    )
    def post(self, request):
        # Validate file
        if 'file' not in request.FILES:
            return Response(
                {'code': 'FILE_REQUIRED', 'message': 'Invoice file is required.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        # Parse form data
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            invoice = InvoiceService.create(
                name=serializer.validated_data['name'],
                amount=serializer.validated_data['amount'],
                category=serializer.validated_data['category'],
                custom_type=serializer.validated_data.get('custom_type', ''),
                project=serializer.validated_data.get('project', ''),
                item_id=serializer.validated_data.get('item_id'),
                file=file,
                filename=file.name,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = InvoiceSerializer(invoice)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class InvoiceDetailView(APIView):
    """Retrieve, update, and delete an invoice."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Get invoice by ID."""
        try:
            return InvoiceService.get(pk)
        except Invoice.DoesNotExist:
            return None
    
    @extend_schema(
        responses={
            200: InvoiceSerializer,
            404: OpenApiResponse(description='Invoice not found'),
        },
        tags=['Invoices'],
        summary='Get invoice',
        description='Get invoice details by ID.',
    )
    def get(self, request, pk):
        invoice = self.get_object(pk)
        if not invoice:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        request=InvoiceUpdateSerializer,
        responses={
            200: InvoiceSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Invoice not found'),
            409: OpenApiResponse(description='Business conflict'),
        },
        tags=['Invoices'],
        summary='Update invoice',
        description='Update invoice details. Status can only be changed by Super Admin.',
    )
    def patch(self, request, pk):
        invoice = self.get_object(pk)
        if not invoice:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InvoiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            invoice = InvoiceService.update(
                invoice_id=pk,
                operator=request.user,
                name=serializer.validated_data.get('name'),
                amount=serializer.validated_data.get('amount'),
                category=serializer.validated_data.get('category'),
                custom_type=serializer.validated_data.get('custom_type'),
                project=serializer.validated_data.get('project'),
                status=serializer.validated_data.get('status'),
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = InvoiceSerializer(invoice)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Invoice.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT if e.code != 'PERMISSION_DENIED' else status.HTTP_403_FORBIDDEN
            )
    
    @extend_schema(
        responses={
            204: OpenApiResponse(description='Invoice deleted'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Invoice not found'),
        },
        tags=['Invoices'],
        summary='Delete invoice',
        description='Delete an invoice.',
    )
    def delete(self, request, pk):
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            InvoiceService.delete(
                invoice_id=pk,
                operator=request.user,
                ip=ip,
                user_agent=user_agent,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Invoice.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )


class InvoiceStatusUpdateView(APIView):
    """Update invoice status."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=InvoiceStatusUpdateSerializer,
        responses={
            200: InvoiceSerializer,
            400: OpenApiResponse(description='Validation error'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Invoice not found'),
        },
        tags=['Invoices'],
        summary='Update invoice status',
        description='Update invoice reimbursement status.',
    )
    def post(self, request, pk):
        serializer = InvoiceStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
        
        try:
            invoice = InvoiceService.update(
                invoice_id=pk,
                operator=request.user,
                status=serializer.validated_data['status'],
                ip=ip,
                user_agent=user_agent,
            )
            response_serializer = InvoiceSerializer(invoice)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Invoice.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Invoice not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_403_FORBIDDEN
            )


class InvoiceExportView(APIView):
    """Export invoice files to ZIP."""
    permission_classes = [IsSuperAdmin]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='category', description='Filter by category', required=False, type=str),
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='month', description='Filter by registered month (YYYY-MM)', required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(description='ZIP file containing invoice files'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invoices'],
        summary='Export invoice files',
        description='Export invoice original files as ZIP archive. Super Admin only.',
    )
    def get(self, request):
        # Parse filters
        category = request.query_params.get('category')
        status_filter = request.query_params.get('status')
        month = request.query_params.get('month')
        
        invoices = InvoiceService.list(
            category=category,
            status=status_filter,
            registered_month=month,
        )
        
        try:
            zip_content = InvoiceService.export_files_to_zip(invoices)
            
            # Generate filename
            filename = f"invoices_{month or 'all'}.zip"
            
            response = HttpResponse(
                zip_content,
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Invoice IDs to export'},
                },
                'required': ['ids'],
            }
        },
        responses={
            200: OpenApiResponse(description='ZIP file containing invoice files'),
            400: OpenApiResponse(description='No IDs provided'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invoices'],
        summary='Export selected invoice files',
        description='Export selected invoice original files as ZIP archive. Super Admin only.',
    )
    def post(self, request):
        """Export selected invoices by IDs."""
        ids = request.data.get('ids', [])
        
        if not ids:
            return Response(
                {'code': 'NO_IDS', 'message': 'No invoice IDs provided.', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoices = Invoice.objects.filter(id__in=ids)
        
        try:
            zip_content = InvoiceService.export_files_to_zip(invoices)
            
            # Generate filename
            filename = f"invoices_selected_{len(ids)}.zip"
            
            response = HttpResponse(
                zip_content,
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except BusinessConflictError as e:
            return Response(
                {'code': e.code, 'message': e.message, 'details': e.details},
                status=status.HTTP_409_CONFLICT
            )


class InvoiceCategoriesView(APIView):
    """Get all invoice categories."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: {'type': 'array', 'items': {'type': 'string'}}},
        tags=['Invoices'],
        summary='Get invoice categories',
        description='Get all unique invoice categories.',
    )
    def get(self, request):
        categories = InvoiceService.get_categories()
        return Response(categories, status=status.HTTP_200_OK)


class InvoiceMonthsView(APIView):
    """Get all invoice months."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: {'type': 'array', 'items': {'type': 'string'}}},
        tags=['Invoices'],
        summary='Get invoice months',
        description='Get all unique registered months.',
    )
    def get(self, request):
        months = InvoiceService.get_months()
        return Response(months, status=status.HTTP_200_OK)



class InvoiceBatchStatusUpdateView(APIView):
    """Batch update invoice status."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Invoice IDs to update'},
                    'status': {'type': 'string', 'description': 'New status (pending/reimbursed/rejected)'},
                },
                'required': ['ids', 'status'],
            }
        },
        responses={
            200: OpenApiResponse(description='Invoices updated'),
            400: OpenApiResponse(description='Invalid request'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invoices'],
        summary='Batch update invoice status',
        description='Update status for multiple invoices at once.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        new_status = request.data.get('status')
        
        if not ids or not isinstance(ids, list):
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_status:
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'status is required', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status value
        from .models import InvoiceStatus
        valid_statuses = [choice[0] for choice in InvoiceStatus.choices]
        if new_status not in valid_statuses:
            return Response(
                {'code': 'INVALID_STATUS', 'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = Invoice.objects.filter(id__in=ids).update(status=new_status)
        return Response({'updated': updated_count}, status=status.HTTP_200_OK)


class InvoiceBatchDeleteView(APIView):
    """Batch delete invoices."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Invoice IDs to delete'},
                },
                'required': ['ids'],
            }
        },
        responses={
            200: OpenApiResponse(description='Invoices deleted'),
            400: OpenApiResponse(description='Invalid request'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Invoices'],
        summary='Batch delete invoices',
        description='Delete multiple invoices at once.',
    )
    def post(self, request):
        ids = request.data.get('ids', [])
        
        if not ids or not isinstance(ids, list):
            return Response(
                {'code': 'INVALID_REQUEST', 'message': 'ids must be a non-empty list', 'details': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete files first
        import os
        from django.conf import settings
        invoices = Invoice.objects.filter(id__in=ids)
        for invoice in invoices:
            if invoice.file:
                file_path = os.path.join(settings.MEDIA_ROOT, invoice.file)
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        deleted_count, _ = Invoice.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted_count}, status=status.HTTP_200_OK)
