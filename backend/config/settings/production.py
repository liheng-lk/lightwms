"""
Production settings for LightWMS project.
"""
import os
from .base import *

DEBUG = False

# Production must never silently start with development fallback credentials.
if not os.environ.get('SECRET_KEY'):
    raise RuntimeError('SECRET_KEY must be set in production.')
if not os.environ.get('POSTGRES_PASSWORD'):
    raise RuntimeError('POSTGRES_PASSWORD must be set in production.')

# 允许的主机名（支持通配符和空值处理）
_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
if _allowed_hosts == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]

# CSRF 信任的源（用于跨域 POST 请求）
_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Cookie 安全设置（根据环境变量决定是否强制 HTTPS）
# 内网 HTTP 部署时需要设置 SECURE_COOKIES=false
_secure_cookies = os.environ.get('SECURE_COOKIES', 'true').lower() == 'true'
CSRF_COOKIE_SECURE = _secure_cookies
SESSION_COOKIE_SECURE = _secure_cookies

# HTTPS 重定向设置
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/lightwms/app.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
