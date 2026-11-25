"""
Views for webhook endpoint management.

Super Admin only. Provides CRUD for webhook endpoints and
a test endpoint action.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsSuperAdmin
from .services.webhook_service import WebhookService
from .webhook_serializers import (
    WebhookEndpointSerializer,
    WebhookEndpointCreateSerializer,
    WebhookEndpointUpdateSerializer,
)
from .webhook_models import WebhookEndpoint, WebhookEvent


class WebhookEndpointListCreateView(APIView):
    """List and create webhook endpoints."""
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        responses={200: WebhookEndpointSerializer(many=True)},
        tags=['Webhooks'],
        summary='List webhook endpoints',
    )
    def get(self, request):
        endpoints = WebhookService.list_endpoints(active_only=False)
        serializer = WebhookEndpointSerializer(endpoints, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=WebhookEndpointCreateSerializer,
        responses={
            201: WebhookEndpointSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
        tags=['Webhooks'],
        summary='Create webhook endpoint',
    )
    def post(self, request):
        serializer = WebhookEndpointCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        endpoint = WebhookService.create_endpoint(
            url=serializer.validated_data['url'],
            events=serializer.validated_data['events'],
            name=serializer.validated_data.get('name', ''),
            secret=serializer.validated_data.get('secret', ''),
            is_active=serializer.validated_data.get('is_active', True),
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )

        response_serializer = WebhookEndpointSerializer(endpoint)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class WebhookEndpointDetailView(APIView):
    """Get, update, and delete webhook endpoints."""
    permission_classes = [IsSuperAdmin]

    def get_object(self, pk):
        try:
            return WebhookEndpoint.objects.get(pk=pk)
        except WebhookEndpoint.DoesNotExist:
            return None

    @extend_schema(
        responses={
            200: WebhookEndpointSerializer,
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Webhooks'],
        summary='Get webhook endpoint',
    )
    def get(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Webhook endpoint not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = WebhookEndpointSerializer(endpoint)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=WebhookEndpointUpdateSerializer,
        responses={
            200: WebhookEndpointSerializer,
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Webhooks'],
        summary='Update webhook endpoint',
    )
    def patch(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Webhook endpoint not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WebhookEndpointUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        endpoint = WebhookService.update_endpoint(
            endpoint_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
            **serializer.validated_data,
        )

        response_serializer = WebhookEndpointSerializer(endpoint)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            204: OpenApiResponse(description='Deleted'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Webhooks'],
        summary='Delete webhook endpoint',
    )
    def delete(self, request, pk):
        endpoint = self.get_object(pk)
        if not endpoint:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Webhook endpoint not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )

        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))

        WebhookService.delete_endpoint(
            endpoint_id=pk,
            operator=request.user,
            ip=ip,
            user_agent=user_agent,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookEndpointTestView(APIView):
    """Send a test event to a webhook endpoint."""
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        responses={
            200: dict,
            404: OpenApiResponse(description='Not found'),
        },
        tags=['Webhooks'],
        summary='Test webhook endpoint',
    )
    def post(self, request, pk):
        try:
            result = WebhookService.test_endpoint(endpoint_id=pk)
            return Response(result, status=status.HTTP_200_OK)
        except WebhookEndpoint.DoesNotExist:
            return Response(
                {'code': 'NOT_FOUND', 'message': 'Webhook endpoint not found.', 'details': None},
                status=status.HTTP_404_NOT_FOUND,
            )


class WebhookEventListView(APIView):
    """List all available webhook event types."""
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        responses={200: dict},
        tags=['Webhooks'],
        summary='List available webhook events',
    )
    def get(self, request):
        events = [
            {'value': choice[0], 'label': choice[1]}
            for choice in WebhookEvent.choices
        ]
        return Response(events, status=status.HTTP_200_OK)
