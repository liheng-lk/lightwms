"""Read invoice attachments from a user-authorized IMAP mailbox."""
from __future__ import annotations

import imaplib
import os
import re
from datetime import date, timedelta
from email import message_from_bytes
from email.header import decode_header
from email.utils import parsedate_to_datetime

from .models import MailboxProvider

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_MESSAGE_BYTES = 15 * 1024 * 1024
MAX_MESSAGES = 40

PROVIDER_HOSTS = {
    MailboxProvider.QQ: ('imap.qq.com', 993),
    MailboxProvider.NETEASE_163: ('imap.163.com', 993),
    MailboxProvider.NETEASE_126: ('imap.126.com', 993),
    MailboxProvider.GMAIL: ('imap.gmail.com', 993),
    MailboxProvider.OUTLOOK: ('outlook.office365.com', 993),
}


class MailboxConnectionError(Exception):
    """Safe, user-facing mailbox failure. Never include the secret."""


def resolve_endpoint(provider: str, host: str = '', port: int | None = None) -> tuple[str, int]:
    if provider == MailboxProvider.CUSTOM:
        cleaned = (host or '').strip().lower()
        if not cleaned or any(char in cleaned for char in ' /\\@'):
            raise MailboxConnectionError('请填写有效的 IMAP 服务器地址。')
        return cleaned, int(port or 993)
    preset = PROVIDER_HOSTS.get(provider)
    if not preset:
        raise MailboxConnectionError('不支持的邮箱类型。')
    return preset


def decode_mime(value: str | None) -> str:
    if not value:
        return ''
    chunks = []
    for text, encoding in decode_header(value):
        if isinstance(text, bytes):
            chunks.append(text.decode(encoding or 'utf-8', 'replace'))
        else:
            chunks.append(text)
    return ''.join(chunks).replace('\x00', '').strip()


def _safe_filename(name: str) -> str:
    base = os.path.basename(name.replace('\\', '/')).strip() or 'invoice'
    return base[:180]


def attachments_from_message(raw: bytes) -> list[dict]:
    message = message_from_bytes(raw)
    subject = decode_mime(message.get('Subject'))[:200]
    sender = decode_mime(message.get('From'))[:200]
    sent_at = ''
    if message.get('Date'):
        try:
            sent_at = parsedate_to_datetime(message.get('Date')).isoformat()
        except (TypeError, ValueError, IndexError):
            sent_at = ''

    found = []
    part_index = 0
    for part in message.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        filename = decode_mime(part.get_filename())
        if not filename:
            continue
        filename = _safe_filename(filename)
        extension = os.path.splitext(filename)[1].lower()
        payload = part.get_payload(decode=True) or b''
        current = part_index
        part_index += 1
        if extension not in ALLOWED_EXTENSIONS or not payload or len(payload) > MAX_ATTACHMENT_BYTES:
            continue
        found.append({
            'part_index': current,
            'filename': filename,
            'size': len(payload),
            'subject': subject,
            'sender': sender,
            'sent_at': sent_at,
            'content': payload,
        })
    return found


def _message_size(imap: imaplib.IMAP4, uid: bytes) -> int | None:
    status, data = imap.uid('FETCH', uid, '(RFC822.SIZE)')
    if status != 'OK' or not data or data[0] is None:
        return None
    blob = data[0][0] if isinstance(data[0], tuple) else data[0]
    if not isinstance(blob, bytes):
        return None
    match = re.search(br'RFC822\.SIZE (\d+)', blob)
    return int(match.group(1)) if match else None


def _message_bytes(imap: imaplib.IMAP4, uid: bytes) -> bytes | None:
    status, data = imap.uid('FETCH', uid, '(BODY.PEEK[])')
    if status != 'OK':
        return None
    for item in data or []:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _announce_client(imap: imaplib.IMAP4) -> None:
    if 'ID' not in imaplib.Commands:
        imaplib.Commands['ID'] = ('NONAUTH', 'AUTH', 'SELECTED')
    try:
        imap._simple_command(  # noqa: SLF001 - NetEase requires this IMAP ID.
            'ID',
            '("name" "LightWMS" "version" "1.2" "vendor" "LightWMS")',
        )
    except imaplib.IMAP4.error:
        return


def connect_mailbox(email_address: str, secret: str, host: str, port: int, provider: str) -> imaplib.IMAP4_SSL:
    try:
        imap = imaplib.IMAP4_SSL(host, port, timeout=20)
        imap.login(email_address, secret)
        if provider in {MailboxProvider.NETEASE_163, MailboxProvider.NETEASE_126}:
            _announce_client(imap)
        return imap
    except imaplib.IMAP4.error as exc:
        detail = str(exc)
        if secret and secret in detail:
            detail = '登录被拒绝'
        raise MailboxConnectionError(
            '邮箱登录失败。请确认已开启 IMAP，并使用邮箱授权码或应用专用密码，而不是网页登录密码。'
            + (f'（{detail[:160]}）' if detail else '')
        ) from exc
    except (TimeoutError, OSError) as exc:
        raise MailboxConnectionError('无法连接邮箱服务器，请检查网络、服务器地址和端口。') from exc


def list_invoice_attachments(account, secret: str, days: int = 45) -> list[dict]:
    days = max(1, min(int(days), 90))
    imap = connect_mailbox(account.email, secret, account.imap_host, account.imap_port, account.provider)
    try:
        status, _ = imap.select('INBOX', readonly=True)
        if status != 'OK':
            raise MailboxConnectionError('无法打开收件箱。')
        since = (date.today() - timedelta(days=days)).strftime('%d-%b-%Y')
        status, data = imap.uid('SEARCH', None, 'SINCE', since)
        if status != 'OK' or not data or not data[0]:
            return []
        uids = data[0].split()[-MAX_MESSAGES:]
        rows = []
        for uid in reversed(uids):
            size = _message_size(imap, uid)
            if size is not None and size > MAX_MESSAGE_BYTES:
                continue
            raw = _message_bytes(imap, uid)
            if not raw:
                continue
            for item in attachments_from_message(raw):
                item.pop('content', None)
                item['uid'] = uid.decode()
                rows.append(item)
                if len(rows) >= 80:
                    return rows
        return rows
    finally:
        try:
            imap.logout()
        except imaplib.IMAP4.error:
            pass


def fetch_attachment(account, secret: str, uid: str, part_index: int) -> dict:
    if not str(uid).isdigit() or int(part_index) < 0:
        raise MailboxConnectionError('附件参数无效。')
    imap = connect_mailbox(account.email, secret, account.imap_host, account.imap_port, account.provider)
    try:
        status, _ = imap.select('INBOX', readonly=True)
        if status != 'OK':
            raise MailboxConnectionError('无法打开收件箱。')
        raw = _message_bytes(imap, str(uid).encode())
        if not raw:
            raise MailboxConnectionError('没有找到这封邮件，可能已被删除。')
        for item in attachments_from_message(raw):
            if item['part_index'] == int(part_index):
                item['uid'] = str(uid)
                return item
        raise MailboxConnectionError('这封邮件里没有可上传的 PDF、JPG 或 PNG 附件。')
    finally:
        try:
            imap.logout()
        except imaplib.IMAP4.error:
            pass
