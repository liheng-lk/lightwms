"""
Utility functions for LightWMS core.
"""


def get_client_info(request):
    """
    Extract client IP and User-Agent from a request.

    The middleware ``RequestContextMiddleware`` sets ``request.client_ip``
    and ``request.user_agent`` on every request.  The ``getattr`` fallbacks
    here ensure this helper still works in test/console contexts where the
    middleware may not have run.

    Returns:
        tuple[str, str]: (ip, user_agent)
    """
    ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
    user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT', ''))
    return ip, user_agent
