"""
Webhook service for LightWMS.

Dispatches event notifications to registered webhook endpoints with
HMAC-SHA256 request signing.
"""
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog, TargetType

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for managing webhook endpoints and dispatching events.

    Event dispatch is intentionally fire-and-forget: webhook delivery
    failures never block or roll back the originating business operation.
    """

    @classmethod
    def list_endpoints(cls, active_only: bool = True):
        """List webhook endpoints."""
        from apps.settings.webhook_models import WebhookEndpoint
        qs = WebhookEndpoint.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by('-created_at')

    @classmethod
    @transaction.atomic
    def create_endpoint(
        cls,
        url: str,
        events: list,
        name: str = '',
        secret: str = '',
        is_active: bool = True,
        operator=None,
        ip: str = '',
        user_agent: str = '',
    ):
        """Create a new webhook endpoint with audit logging."""
        from apps.settings.webhook_models import WebhookEndpoint
        endpoint = WebhookEndpoint.objects.create(
            url=url,
            secret=secret,
            events=events,
            is_active=is_active,
            name=name,
            created_by=operator,
        )

        AuditLog.objects.create(
            action=AuditAction.CREATE,
            target_type=TargetType.SYSTEM,
            target_id=0,
            diff={
                'after': {
                    'type': 'webhook_endpoint',
                    'id': endpoint.id,
                    'name': name,
                    'url': url,
                    'events': events,
                },
            },
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip or None,
            user_agent=user_agent,
        )
        return endpoint

    @classmethod
    @transaction.atomic
    def update_endpoint(
        cls,
        endpoint_id: int,
        operator=None,
        ip: str = '',
        user_agent: str = '',
        **kwargs,
    ):
        """Update a webhook endpoint with audit logging."""
        from apps.settings.webhook_models import WebhookEndpoint
        endpoint = WebhookEndpoint.objects.select_for_update().get(pk=endpoint_id)

        before = {
            'url': endpoint.url,
            'name': endpoint.name,
            'events': endpoint.events,
            'is_active': endpoint.is_active,
        }

        for field in ('url', 'secret', 'events', 'is_active', 'name'):
            if field in kwargs:
                setattr(endpoint, field, kwargs[field])
        endpoint.save()

        after = {
            'url': endpoint.url,
            'name': endpoint.name,
            'events': endpoint.events,
            'is_active': endpoint.is_active,
        }

        AuditLog.objects.create(
            action=AuditAction.UPDATE,
            target_type=TargetType.SYSTEM,
            target_id=0,
            diff={
                'before': {'type': 'webhook_endpoint', 'id': endpoint.id, **before},
                'after': {'type': 'webhook_endpoint', 'id': endpoint.id, **after},
            },
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip or None,
            user_agent=user_agent,
        )
        return endpoint

    @classmethod
    @transaction.atomic
    def delete_endpoint(
        cls,
        endpoint_id: int,
        operator=None,
        ip: str = '',
        user_agent: str = '',
    ):
        """Delete a webhook endpoint with audit logging."""
        from apps.settings.webhook_models import WebhookEndpoint
        endpoint = WebhookEndpoint.objects.get(pk=endpoint_id)

        AuditLog.objects.create(
            action=AuditAction.DELETE,
            target_type=TargetType.SYSTEM,
            target_id=0,
            diff={
                'before': {
                    'type': 'webhook_endpoint',
                    'id': endpoint.id,
                    'name': endpoint.name,
                    'url': endpoint.url,
                },
            },
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip or None,
            user_agent=user_agent,
        )
        endpoint.delete()

    @classmethod
    def _sign_payload(cls, payload_bytes: bytes, secret: str) -> str:
        """Create HMAC-SHA256 signature for a payload."""
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def dispatch_event(
        cls,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Send event to all active endpoints subscribed to the given event.

        This is intentionally fire-and-forget. Delivery failures are logged
        but never propagated to the caller.
        """
        import urllib.request
        import urllib.error

        from apps.settings.webhook_models import WebhookEndpoint

        endpoints = WebhookEndpoint.objects.filter(
            is_active=True,
        )

        payload = json.dumps({
            'event': event,
            'timestamp': timezone.now().isoformat(),
            'data': data,
        }, ensure_ascii=False, default=str)
        payload_bytes = payload.encode('utf-8')

        for endpoint in endpoints:
            # Check if the endpoint is subscribed to this event
            if event not in (endpoint.events or []):
                continue

            try:
                headers = {
                    'Content-Type': 'application/json',
                    'X-Webhook-Event': event,
                }

                if endpoint.secret:
                    signature = cls._sign_payload(payload_bytes, endpoint.secret)
                    headers['X-Webhook-Signature'] = f'sha256={signature}'

                req = urllib.request.Request(
                    endpoint.url,
                    data=payload_bytes,
                    headers=headers,
                    method='POST',
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                logger.warning(
                    'Failed to deliver webhook event %s to %s',
                    event,
                    endpoint.url,
                    exc_info=True,
                )

    @classmethod
    def test_endpoint(cls, endpoint_id: int) -> Dict[str, Any]:
        """Send a test event to a specific endpoint. Returns status info."""
        import urllib.request
        import urllib.error

        from apps.settings.webhook_models import WebhookEndpoint

        endpoint = WebhookEndpoint.objects.get(pk=endpoint_id)

        payload = json.dumps({
            'event': 'test',
            'timestamp': timezone.now().isoformat(),
            'data': {'message': '这是一个测试事件'},
        }, ensure_ascii=False)
        payload_bytes = payload.encode('utf-8')

        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Event': 'test',
        }

        if endpoint.secret:
            signature = cls._sign_payload(payload_bytes, endpoint.secret)
            headers['X-Webhook-Signature'] = f'sha256={signature}'

        try:
            req = urllib.request.Request(
                endpoint.url,
                data=payload_bytes,
                headers=headers,
                method='POST',
            )
            response = urllib.request.urlopen(req, timeout=10)
            return {
                'success': True,
                'status_code': response.status,
                'message': '测试事件发送成功',
            }
        except urllib.error.HTTPError as e:
            return {
                'success': False,
                'status_code': e.code,
                'message': f'远程服务器返回错误: {e.code}',
            }
        except urllib.error.URLError as e:
            return {
                'success': False,
                'status_code': None,
                'message': f'连接失败: {e.reason}',
            }
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'message': f'发送失败: {str(e)}',
            }
