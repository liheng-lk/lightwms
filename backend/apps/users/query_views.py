"""Strict query endpoint for Super Admin user management."""
from datetime import datetime, time

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination
from core.permissions import IsSuperAdmin

from .models import UserRole
from .serializers import UserListSerializer
from .services import UserManagementService


class FlexibleDateTimeField(serializers.Field):
    """Accept ISO datetime or YYYY-MM-DD and reject malformed values."""

    default_error_messages = {'invalid': 'Expected an ISO datetime or YYYY-MM-DD date.'}

    def to_internal_value(self, data):
        if not isinstance(data, str) or not data.strip():
            self.fail('invalid')
        text = data.strip()
        try:
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


def _range_boundary(value, *, end: bool):
    if value is None:
        return None
    kind, parsed = value
    if kind == 'datetime':
        return parsed
    boundary = time.max if end else time.min
    result = datetime.combine(parsed, boundary)
    return timezone.make_aware(result, timezone.get_current_timezone())


class UserListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100, trim_whitespace=True)
    role = serializers.ChoiceField(required=False, choices=UserRole.choices)
    is_active = serializers.BooleanField(required=False)
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


def _invalid(errors):
    return Response(
        {
            'code': 'VALIDATION_ERROR',
            'message': 'Invalid user list query parameters.',
            'details': errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


class UserListView(APIView):
    """List active/non-deleted users with strict, explicit query semantics."""

    permission_classes = [IsSuperAdmin]
    pagination_class = StandardPagination

    @extend_schema(
        parameters=[
            OpenApiParameter('search', str, required=False, description='Username substring'),
            OpenApiParameter(
                'role', str, required=False, enum=[choice[0] for choice in UserRole.choices]
            ),
            OpenApiParameter('is_active', bool, required=False),
            OpenApiParameter('date_from', str, required=False, description='ISO datetime or YYYY-MM-DD'),
            OpenApiParameter('date_to', str, required=False, description='ISO datetime or YYYY-MM-DD'),
            OpenApiParameter('page', int, required=False),
            OpenApiParameter('page_size', int, required=False),
        ],
        responses={
            200: UserListSerializer(many=True),
            400: OpenApiResponse(description='Invalid query parameter'),
            403: OpenApiResponse(description='Permission denied'),
        },
        tags=['Users'],
        summary='List users',
        description='List users with validated search, role, status, and date filters. Super Admin only.',
    )
    def get(self, request):
        query = UserListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return _invalid(query.errors)
        data = query.validated_data

        users = UserManagementService().list_users(
            role=data.get('role'),
            is_active=data.get('is_active'),
            date_from=data.get('_start'),
            date_to=data.get('_end'),
        )
        search = data.get('search')
        if search:
            users = users.filter(username__icontains=search)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(users, request)
        if page is not None:
            return paginator.get_paginated_response(UserListSerializer(page, many=True).data)
        return Response(UserListSerializer(users, many=True).data, status=status.HTTP_200_OK)
