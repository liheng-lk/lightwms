"""Custom middleware for LightWMS."""
import ipaddress

from django.conf import settings


class RequestContextMiddleware:
    """Attach a trustworthy client IP and User-Agent to each request.

    Forwarded headers are security-sensitive because login rate limiting and
    LoginLog both depend on ``client_ip``. They are honored only when the
    immediate TCP peer is within an explicitly configured trusted proxy CIDR.
    The shipped Nginx config overwrites X-Real-IP with ``$remote_addr``, so it
    is preferred over client-appendable X-Forwarded-For.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.client_ip = self.get_client_ip(request)
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')
        return self.get_response(request)

    @staticmethod
    def _parse_ip(value):
        try:
            return ipaddress.ip_address(str(value or '').strip())
        except ValueError:
            return None

    def _trusted_proxy_networks(self):
        networks = []
        for cidr in getattr(settings, 'TRUSTED_PROXY_CIDRS', []):
            try:
                networks.append(ipaddress.ip_network(str(cidr).strip(), strict=False))
            except ValueError:
                # Invalid deployment config must not make arbitrary peers
                # trusted; skip it and fall back to REMOTE_ADDR.
                continue
        return networks

    def _is_trusted_proxy(self, remote_ip) -> bool:
        return remote_ip is not None and any(
            remote_ip in network for network in self._trusted_proxy_networks()
        )

    def get_client_ip(self, request):
        remote_text = request.META.get('REMOTE_ADDR', '')
        remote_ip = self._parse_ip(remote_text)

        if not self._is_trusted_proxy(remote_ip):
            return str(remote_ip) if remote_ip is not None else remote_text.strip()

        # Nginx in docker/nginx/conf.d/default.conf sets this header from
        # $remote_addr and therefore replaces, rather than appends to, any
        # client-supplied value.
        real_ip = self._parse_ip(request.META.get('HTTP_X_REAL_IP'))
        if real_ip is not None:
            return str(real_ip)

        # Fallback for trusted proxies that provide only X-Forwarded-For. Walk
        # right-to-left and strip known proxy hops; never trust the first value
        # merely because the header exists.
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        chain = [self._parse_ip(part) for part in xff.split(',') if part.strip()]
        chain = [ip for ip in chain if ip is not None]
        trusted = self._trusted_proxy_networks()
        for candidate in reversed(chain):
            if not any(candidate in network for network in trusted):
                return str(candidate)

        return str(remote_ip) if remote_ip is not None else remote_text.strip()
