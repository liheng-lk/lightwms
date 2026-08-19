"""Application version and update-check endpoint."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


_VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
_DOCKERHUB_TAGS_API = os.getenv(
    'UPDATE_CHECK_URL',
    'https://hub.docker.com/v2/namespaces/liheng6668/repositories/lightwms-backend/tags?page_size=100',
)
_DOCKERHUB_RELEASE_PAGE = 'https://hub.docker.com/r/liheng6668/lightwms-backend/tags'
_CACHE_KEY = 'lightwms:version-check:v1'
_CACHE_SECONDS = 30 * 60


def _version_tuple(value: str | None):
    if not value:
        return None
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _read_current_version() -> str:
    env_version = (os.getenv('APP_VERSION') or '').strip()
    if _version_tuple(env_version):
        return env_version.lstrip('v')

    candidates = [
        Path('/app/VERSION'),
        Path(settings.BASE_DIR).parent / 'VERSION',
        Path(settings.BASE_DIR) / 'VERSION',
    ]
    for path in candidates:
        try:
            value = path.read_text(encoding='utf-8').strip()
        except (OSError, UnicodeError):
            continue
        if _version_tuple(value):
            return value.lstrip('v')
    return 'unknown'


def _latest_dockerhub_version() -> str:
    request = urllib.request.Request(
        _DOCKERHUB_TAGS_API,
        headers={'Accept': 'application/json', 'User-Agent': 'LightWMS-UpdateChecker/1.0'},
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        payload = json.loads(response.read().decode('utf-8'))

    versions: list[tuple[tuple[int, int, int], str]] = []
    for row in payload.get('results', []):
        name = str(row.get('name') or '').strip()
        parsed = _version_tuple(name)
        if parsed:
            versions.append((parsed, name.lstrip('v')))
    if not versions:
        raise ValueError('DockerHub 中没有找到语义化版本标签')
    versions.sort(key=lambda item: item[0], reverse=True)
    return versions[0][1]


def get_version_status(force: bool = False) -> dict:
    current = _read_current_version()
    if not force:
        cached = cache.get(_CACHE_KEY)
        if isinstance(cached, dict) and cached.get('current_version') == current:
            return cached

    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        latest = _latest_dockerhub_version()
        current_tuple = _version_tuple(current)
        latest_tuple = _version_tuple(latest)
        update_available = bool(
            current_tuple and latest_tuple and latest_tuple > current_tuple
        )
        result = {
            'current_version': current,
            'latest_version': latest,
            'update_available': update_available,
            'check_ok': True,
            'checked_at': checked_at,
            'release_url': _DOCKERHUB_RELEASE_PAGE,
            'message': f'发现新版本 {latest}' if update_available else '当前已是最新版本',
        }
    except Exception:
        # Network/update-source problems must never make the WMS unavailable.
        result = {
            'current_version': current,
            'latest_version': None,
            'update_available': False,
            'check_ok': False,
            'checked_at': checked_at,
            'release_url': _DOCKERHUB_RELEASE_PAGE,
            'message': '版本检查暂时不可用',
        }

    cache.set(_CACHE_KEY, result, _CACHE_SECONDS)
    return result


class VersionCheckView(APIView):
    """Return the installed version and the newest published Docker image tag."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        force = request.query_params.get('force', '').lower() in {'1', 'true', 'yes'}
        return Response(get_version_status(force=force), status=status.HTTP_200_OK)
