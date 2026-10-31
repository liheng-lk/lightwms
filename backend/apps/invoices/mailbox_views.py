"""Authorize mailboxes and import invoice attachments."""
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsItemManagerOrSuperAdmin

from .mailbox_crypto import decrypt_secret, encrypt_secret
from .mailbox_imap import (
    MailboxConnectionError,
    connect_mailbox,
    fetch_attachment,
    list_invoice_attachments,
    login_from_email,
    resolve_endpoint,
)
from .models import Invoice, MailboxAccount, MailboxProvider
from .serializers import InvoiceSerializer
from .services import InvoiceService


def _error(message: str, code: str = 'MAILBOX_ERROR', http_status: int = status.HTTP_400_BAD_REQUEST):
    return Response({'code': code, 'message': message, 'details': None}, status=http_status)


def _owned(request, pk: int) -> MailboxAccount | None:
    return MailboxAccount.objects.filter(pk=pk, user=request.user).first()


def _public(account: MailboxAccount) -> dict:
    return {
        'id': account.id,
        'label': account.label,
        'email': account.email,
        'provider': account.provider,
        'imap_host': account.imap_host,
        'imap_port': account.imap_port,
        'last_error': account.last_error,
        'created_at': account.created_at.isoformat() if account.created_at else None,
    }


class MailboxListCreateView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request):
        accounts = MailboxAccount.objects.filter(user=request.user)
        return Response([_public(account) for account in accounts])

    def post(self, request):
        email = str(request.data.get('email') or '').strip().lower()
        secret = str(request.data.get('secret') or '')
        label = str(request.data.get('label') or '').strip()[:80]
        provider = str(request.data.get('provider') or '').strip()
        if not email or '@' not in email:
            return _error('请填写邮箱地址。')
        if not secret or len(secret) > 200:
            return _error('请填写邮箱登录密码。')
        try:
            if provider == MailboxProvider.CUSTOM and request.data.get('imap_host'):
                host, port = resolve_endpoint(
                    provider,
                    str(request.data.get('imap_host') or ''),
                    request.data.get('imap_port') or None,
                )
            elif provider in MailboxProvider.values and provider != MailboxProvider.CUSTOM:
                host, port = resolve_endpoint(provider)
            else:
                provider, host, port = login_from_email(email)
        except (MailboxConnectionError, TypeError, ValueError) as exc:
            return _error(str(exc))

        try:
            imap = connect_mailbox(email, secret, host, port, provider)
            imap.logout()
        except MailboxConnectionError as exc:
            return _error(str(exc))

        account, _created = MailboxAccount.objects.update_or_create(
            user=request.user,
            email=email,
            defaults={
                'label': label,
                'provider': provider,
                'imap_host': host,
                'imap_port': port,
                'secret_encrypted': encrypt_secret(secret),
                'last_error': '',
            },
        )
        return Response(_public(account), status=status.HTTP_201_CREATED)


class MailboxDetailView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def delete(self, request, pk: int):
        account = _owned(request, pk)
        if account is None:
            return _error('邮箱不存在。', 'MAILBOX_NOT_FOUND', status.HTTP_404_NOT_FOUND)
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MailboxAttachmentListView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def get(self, request, pk: int):
        account = _owned(request, pk)
        if account is None:
            return _error('邮箱不存在。', 'MAILBOX_NOT_FOUND', status.HTTP_404_NOT_FOUND)
        try:
            secret = decrypt_secret(account.secret_encrypted)
            days = int(request.query_params.get('days') or 45)
            rows = list_invoice_attachments(account, secret, days)
        except (MailboxConnectionError, ValueError) as exc:
            account.last_error = str(exc)[:300]
            account.save(update_fields=['last_error', 'updated_at'])
            return _error(str(exc))

        keys = [f'{account.id}:{row["uid"]}:{row["part_index"]}' for row in rows]
        imported = set(
            Invoice.objects.filter(source_key__in=keys).values_list('source_key', flat=True)
        )
        if account.last_error:
            account.last_error = ''
            account.save(update_fields=['last_error', 'updated_at'])
        return Response([
            {
                'uid': row['uid'],
                'part_index': row['part_index'],
                'filename': row['filename'],
                'size': row['size'],
                'subject': row['subject'],
                'sender': row['sender'],
                'sent_at': row['sent_at'],
                'imported': f'{account.id}:{row["uid"]}:{row["part_index"]}' in imported,
            }
            for row in rows
        ])


class MailboxImportView(APIView):
    permission_classes = [IsItemManagerOrSuperAdmin]

    def post(self, request, pk: int):
        account = _owned(request, pk)
        if account is None:
            return _error('邮箱不存在。', 'MAILBOX_NOT_FOUND', status.HTTP_404_NOT_FOUND)

        name = str(request.data.get('name') or '').strip()[:200]
        category = str(request.data.get('category') or '').strip()[:100]
        custom_type = str(request.data.get('custom_type') or '').strip()[:100]
        project = str(request.data.get('project') or '').strip()[:200]
        uid = str(request.data.get('uid') or '').strip()
        try:
            part_index = int(request.data.get('part_index'))
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError, ValueError):
            return _error('请填写有效的金额，并选择一个附件。')
        if not name or not category:
            return _error('请填写发票名称和类别。')
        if amount < 0:
            return _error('金额不能为负数。')

        source_key = f'{account.id}:{uid}:{part_index}'
        if Invoice.objects.filter(source_key=source_key).exists():
            return _error('这个附件已经导入过。', 'ALREADY_IMPORTED', status.HTTP_409_CONFLICT)

        try:
            secret = decrypt_secret(account.secret_encrypted)
            attachment = fetch_attachment(account, secret, uid, part_index)
        except (MailboxConnectionError, ValueError) as exc:
            return _error(str(exc))

        upload = BytesIO(attachment['content'])
        upload.seek(0)
        try:
            with transaction.atomic():
                invoice = InvoiceService.create(
                    name=name,
                    amount=amount,
                    category=category,
                    file=upload,
                    filename=attachment['filename'],
                    operator=request.user,
                    custom_type=custom_type,
                    project=project,
                    ip=getattr(request, 'client_ip', request.META.get('REMOTE_ADDR')),
                    user_agent=getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', '')),
                )
                invoice.mailbox = account
                invoice.source_key = source_key
                invoice.save(update_fields=['mailbox', 'source_key', 'updated_at'])
        except IntegrityError:
            return _error('这个附件已经导入过。', 'ALREADY_IMPORTED', status.HTTP_409_CONFLICT)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
