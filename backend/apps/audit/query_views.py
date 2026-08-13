"""Strict, super-admin-only query endpoints for immutable audit data."""
from datetime import datetime, time

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination
from core.permissions import IsSuperAdmin

from .models import AuditAction, AuditLog, LoginLog, TargetType
from .serializers import AuditLogSerializer, LoginLogSerializer
from .services import AuditService


MAX_BIGINT_ID = 9_223_372_036_854_775_807


class FlexibleDateTimeField(serializers.Field):
    """Accept ISO datetime or YYYY-MM-DD while rejecting malformed input."""

    default_error_messages = {'invalid': 'Expected an ISO datetime or YYYY-MM-DD date.'}

    def to_internal_value(self, data):
        if not isinstance(data, str) or not data.strip():
            self.fail('invalid')
        text = data.strip()
        try:
            # Date-only filters remain convenient for the existing UI.
            if len(text) == 10 and text[4] == '-' and text[7] == '-':
                parsed_date = datetime.strptime(text, '%Y-%m-%d').date()
                return ('date', parsed_date)

            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            return ('datetime', parsed)
        except (TypeError, ValueError, OverflowError):
            self.fail('invalid')

    def to_representation(self, value):
        return value


class DateRangeMixin(serializers.Serializer):
    date_from = FlexibleDateTimeField(required=False)
    date_to = FlexibleDateTimeField(required=False)

    def validate(self, attrs):
        start = _range_boundary(attrs.get('date_from'), end=False)
        end = _range_boundary(attrs.get('date_to'), end=True)
        if start and end and start > end:
            raise serializers.ValidationError(
                {'date_to': ['date_to must be on or after date_from.']}
            )
        attrs['_start'] = start
        attrs['_end'] = end
        return attrs


def _range_boundary(value, *, end):
    if value is None:
        return None
    kind, parsed = value
    if kind == 'datetime':
        return parsed
    boundary = time.max if end else time.min
    dt = datetime.combine(parsed, boundary)
    return timezone.make_aware(dt, timezone.get_current_timezone())


class AuditListQuerySerializer(DateRangeMixin):
    action = serializers.ChoiceField(required=False, choices=AuditAction.choices)
    target_type = serializers.ChoiceField(required=False, choices=TargetType.choices)
    operator_id = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_BIGINT_ID
    )


class LoginListQuerySerializer(DateRangeMixin):
    user_id = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_BIGINT_ID
    )
    success = serializers.BooleanField(required=False)
    ip = serializers.IPAddressField(required=False)


class ResourceHistoryQuerySerializer(DateRangeMixin):
    action = serializers.ChoiceField(required=False, choices=AuditAction.choices)


class ResourcePathSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=TargetType.choices)
    target_id = serializers.IntegerField(min_value=0, max_value=MAX_BIGINT_ID)


class UserActivityQuerySerializer(DateRangeMixin):
    action = serializers.ChoiceField(required=False, choices=AuditAction.choices)
    target_type = serializers.ChoiceField(required=False, choices=TargetType.choices)


class UserPathSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1, max_value=MAX_BIGINT_ID)


def _invalid(errors):
    return Response(
        {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid audit query parameters.',
            'details': errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _paginate(request, queryset, serializer_class):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        return paginator.get_paginated_response(serializer_class(page, many=True).data)
    return Response(serializer_class(queryset, many=True).data, status=status.HTTP_200_OK)


class AuditLogListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        query = AuditListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid(query.errors)
        data = query.validated_data

        queryset = AuditLog.objects.select_related('operator').all()
        if data.get('action'):
            queryset = queryset.filter(action=data['action'])
        if data.get('target_type'):
            queryset = queryset.filter(target_type=data['target_type'])
        if data.get('operator_id') is not None:
            queryset = queryset.filter(operator_id=data['operator_id'])
        if data.get('_start'):
            queryset = queryset.filter(created_at__gte=data['_start'])
        if data.get('_end'):
            queryset = queryset.filter(created_at__lte=data['_end'])
        return _paginate(request, queryset.order_by('-created_at'), AuditLogSerializer)


class AuditLogResourceHistoryView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, type, id):
        path = ResourcePathSerializer(data={'target_type': type, 'target_id': id})
        query = ResourceHistoryQuerySerializer(data=request.query_params)
        if not path.is_valid() or not query.is_valid():
            errors = {}
            if not path.is_valid():
                errors.update(path.errors)
            if not query.is_valid():
                errors.update(query.errors)
            return _invalid(errors)

        q = query.validated_data
        queryset = AuditService.get_resource_history(
            target_type=path.validated_data['target_type'],
            target_id=path.validated_data['target_id'],
            action=q.get('action'),
            start_date=q.get('_start'),
            end_date=q.get('_end'),
        ).select_related('operator')
        return _paginate(request, queryset, AuditLogSerializer)


class AuditLogUserActivityView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, id):
        path = UserPathSerializer(data={'user_id': id})
        query = UserActivityQuerySerializer(data=request.query_params)
        if not path.is_valid() or not query.is_valid():
            errors = {}
            if not path.is_valid():
                errors.update(path.errors)
            if not query.is_valid():
                errors.update(query.errors)
            return _invalid(errors)

        q = query.validated_data
        queryset = AuditService.get_user_activity(
            user_id=path.validated_data['user_id'],
            action=q.get('action'),
            target_type=q.get('target_type'),
            start_date=q.get('_start'),
            end_date=q.get('_end'),
        ).select_related('operator')
        return _paginate(request, queryset, AuditLogSerializer)


class LoginLogListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        query = LoginListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid(query.errors)
        data = query.validated_data

        queryset = LoginLog.objects.select_related('user').all()
        if data.get('user_id') is not None:
            queryset = queryset.filter(user_id=data['user_id'])
        if 'success' in data:
            queryset = queryset.filter(success=data['success'])
        if data.get('ip'):
            queryset = queryset.filter(ip=data['ip'])
        if data.get('_start'):
            queryset = queryset.filter(created_at__gte=data['_start'])
        if data.get('_end'):
            queryset = queryset.filter(created_at__lte=data['_end'])
        return _paginate(request, queryset.order_by('-created_at'), LoginLogSerializer)
