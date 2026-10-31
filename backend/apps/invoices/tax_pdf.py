"""Download the official invoice PDF behind a tax-bureau QR link."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse
import urllib.error
import urllib.request

MAX_PDF_BYTES = 10 * 1024 * 1024
_ALLOWED_PORTS = {443, 8443}
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/pdf,text/html;q=0.8,*/*;q=0.5',
}
_HREF = re.compile(r'''(?:href|src)\s*=\s*['"]([^'"]+)['"]''', re.I)


class TaxPdfError(Exception):
    """The tax site did not yield an official PDF."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _public_host(host: str, port: int) -> None:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise TaxPdfError('无法解析发票下载地址。') from exc
    if not addresses:
        raise TaxPdfError('无法解析发票下载地址。')
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global:
            raise TaxPdfError('发票下载地址不可用。')


def validate_tax_url(url: str) -> str:
    parsed = urlparse((url or '').strip())
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme != 'https' or not host:
        raise TaxPdfError('只接受税务网站的 https 链接。')
    if host != 'chinatax.gov.cn' and not host.endswith('.chinatax.gov.cn'):
        raise TaxPdfError('这不是税务发票下载链接。')
    port = parsed.port or 443
    if port not in _ALLOWED_PORTS:
        raise TaxPdfError('发票下载端口不受支持。')
    _public_host(host, port)
    return parsed.geturl()


def next_pdf_link(html: str, base: str) -> str | None:
    for raw in _HREF.findall(html or ''):
        candidate = urljoin(base, raw.strip())
        lowered = candidate.lower()
        if '.pdf' in lowered or 'wjgs=pdf' in lowered or 'exportdzfp' in lowered:
            return candidate
    return None


def _filename(url: str) -> str:
    number = re.search(r'(\d{8,20})', url)
    return f'发票{number.group(1)}.pdf' if number else '发票.pdf'


def download_tax_pdf(url: str) -> tuple[bytes, str]:
    current = validate_tax_url(url)
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(5):
        request = urllib.request.Request(current, headers=_HEADERS)
        try:
            with opener.open(request, timeout=20) as response:
                payload = response.read(MAX_PDF_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get('Location') or ''
                current = validate_tax_url(urljoin(current, location))
                continue
            raise TaxPdfError('税务网站没有返回发票 PDF，请手动上传 PDF 文件。') from exc
        except (TimeoutError, urllib.error.URLError, OSError) as exc:
            raise TaxPdfError('无法连接税务网站，请稍后重试或手动上传 PDF。') from exc
        if len(payload) > MAX_PDF_BYTES:
            raise TaxPdfError('发票 PDF 超过 10MB。')
        if payload.startswith(b'%PDF-'):
            return payload, _filename(current)
        follow = next_pdf_link(payload.decode('utf-8', 'ignore'), current)
        if not follow:
            raise TaxPdfError('税务网站没有返回发票 PDF。请下载 PDF 后用「新增发票」上传。')
        current = validate_tax_url(follow)
    raise TaxPdfError('发票下载跳转过多，请手动上传 PDF。')
