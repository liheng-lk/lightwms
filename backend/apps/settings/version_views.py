"""Application version and update-check endpoint.

An update is reported when either:

1. DockerHub has a semantic-version tag newer than the running version, or
2. the tag this deployment tracks (``IMAGE_TAG``, e.g. ``latest`` or
   ``1.2.1``) was pushed again after this image was built. This catches
   re-published images where the version number was not bumped.

Both the backend and the frontend repositories are checked, so pushing only a
new frontend image is detected too.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSuperAdmin


_VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
_DOCKERHUB_NAMESPACE = os.getenv('UPDATE_CHECK_NAMESPACE', 'liheng6668')
_REPOSITORIES = ('lightwms-backend', 'lightwms-frontend')
_DOCKERHUB_TAGS_API = (
    'https://hub.docker.com/v2/namespaces/{namespace}/repositories/{repo}/tags'
    '?page_size=100&ordering=last_updated'
)
_DOCKERHUB_RELEASE_PAGE = f'https://hub.docker.com/r/{_DOCKERHUB_NAMESPACE}/lightwms-backend/tags'
_CACHE_KEY = 'lightwms:version-check:v2'
_CACHE_SECONDS = 30 * 60
# The workflow builds the backend first and pushes afterwards; a push this
# soon after our own build time is the same release, not a newer one.
_PUSH_GRACE = timedelta(minutes=30)


def _version_tuple(value: str | None):
    if not value:
        return None
    match = _VERSION_RE.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _parse_time(value: str | None):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


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


def _tracked_tag(current: str) -> str:
    tag = (os.getenv('IMAGE_TAG') or '').strip()
    if tag:
        return tag
    return current if _version_tuple(current) else 'latest'


def _fetch_tags(repo: str) -> list[dict]:
    url = os.getenv('UPDATE_CHECK_URL') if repo == 'lightwms-backend' else None
    url = url or _DOCKERHUB_TAGS_API.format(namespace=_DOCKERHUB_NAMESPACE, repo=repo)
    request = urllib.request.Request(
        url,
        headers={'Accept': 'application/json', 'User-Agent': 'LightWMS-UpdateChecker/2.0'},
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        payload = json.loads(response.read().decode('utf-8'))
    return list(payload.get('results', []))


def _evaluate(current: str, build_time, tracked_tag: str, tags_by_repo: dict) -> dict:
    newest = None
    republished_at = None
    for rows in tags_by_repo.values():
        for row in rows:
            name = str(row.get('name') or '').strip()
            parsed = _version_tuple(name)
            if parsed and (newest is None or parsed > newest[0]):
                newest = (parsed, name.lstrip('v'))
            if name == tracked_tag and build_time is not None:
                pushed = _parse_time(row.get('last_updated') or row.get('tag_last_pushed'))
                if pushed and pushed > build_time + _PUSH_GRACE:
                    if republished_at is None or pushed > republished_at:
                        republished_at = pushed

    current_tuple = _version_tuple(current)
    latest_version = newest[1] if newest else None

    if newest and current_tuple and newest[0] > current_tuple:
        return {
            'latest_version': latest_version,
            'update_available': True,
            'update_reason': 'new_version',
            'message': f'发现新版本 v{latest_version}',
        }
    if republished_at is not None:
        return {
            'latest_version': latest_version or current,
            'update_available': True,
            'update_reason': 'image_republished',
            'published_at': republished_at.isoformat(),
            'message': f'镜像 {tracked_tag} 已重新发布',
        }
    return {
        'latest_version': latest_version,
        'update_available': False,
        'update_reason': None,
        'message': '当前已是最新版本',
    }


def get_version_status(force: bool = False) -> dict:
    current = _read_current_version()
    build_time = _parse_time(os.getenv('BUILD_TIME'))
    tracked_tag = _tracked_tag(current)

    if not force:
        cached = cache.get(_CACHE_KEY)
        if isinstance(cached, dict) and cached.get('current_version') == current \
                and cached.get('build_time') == (build_time.isoformat() if build_time else None):
            return cached

    base = {
        'current_version': current,
        'build_time': build_time.isoformat() if build_time else None,
        'revision': (os.getenv('APP_REVISION') or '')[:12] or None,
        'image_tag': tracked_tag,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'release_url': _DOCKERHUB_RELEASE_PAGE,
        # Without a build time we can only compare version numbers.
        'detects_republish': build_time is not None,
    }

    tags_by_repo = {}
    for repo in _REPOSITORIES:
        try:
            tags_by_repo[repo] = _fetch_tags(repo)
        except Exception:
            continue

    if not tags_by_repo:
        # Network/update-source problems must never make the WMS unavailable.
        result = {
            **base,
            'latest_version': None,
            'update_available': False,
            'update_reason': None,
            'check_ok': False,
            'message': '版本检查暂时不可用（无法访问 DockerHub）',
        }
    else:
        result = {**base, **_evaluate(current, build_time, tracked_tag, tags_by_repo), 'check_ok': True}

    cache.set(_CACHE_KEY, result, _CACHE_SECONDS)
    return result


class VersionCheckView(APIView):
    """Return the installed version and whether a newer image is published."""

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Forcing a fresh DockerHub lookup bypasses the cache; restrict it so
        # ordinary users cannot make the server hammer DockerHub.
        if self.request.query_params.get('force', '').lower() in {'1', 'true', 'yes'}:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        force = request.query_params.get('force', '').lower() in {'1', 'true', 'yes'}
        return Response(get_version_status(force=force), status=status.HTTP_200_OK)
