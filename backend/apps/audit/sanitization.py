"""Central sanitization for immutable audit payloads."""
from copy import deepcopy


REDACTED = '[REDACTED]'
SENSITIVE_KEYS = {
    'password',
    'password_hash',
    'old_password',
    'new_password',
    'current_password',
    'token',
    'access_token',
    'refresh_token',
    'api_key',
    'secret',
    'secret_key',
    'client_secret',
    'authorization',
    'proxy_authorization',
    'cookie',
    'set_cookie',
    'session',
    'sessionid',
    'wechat_session',
}


def _normalise_key(key) -> str:
    return str(key).strip().lower().replace('-', '_').replace(' ', '_')


def sanitize_audit_data(value):
    """Recursively replace sensitive values while preserving audit structure."""
    if isinstance(value, dict):
        result = {}
        for key, nested in value.items():
            if _normalise_key(key) in SENSITIVE_KEYS:
                result[key] = REDACTED
            else:
                result[key] = sanitize_audit_data(nested)
        return result
    if isinstance(value, list):
        return [sanitize_audit_data(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_audit_data(item) for item in value]
    return deepcopy(value)
