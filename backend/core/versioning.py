"""Application version discovery and remote update checks."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils import timezone


DEFAULT_UPDATE_CHECK_URL = (
    'https://hub.docker.com/v2/repositories/'
    'liheng6668/lightwms-backend/tags?page_size=100'
)
_VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:[-.+][0-9A-Za-z.-]+)?$')


def _version_key(value: str):
    match = _VERSION_RE.match((value or '').strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def get_current_version() -> str:
    """Read the running version from env or the repository/image VERSION file."""
    env_version = os.getenv('LIGHTWMS_VERSION', '').strip()
    if env_version:
        return env_version

    candidates = [
        Path('/app/VERSION'),
        Path(__file__).resolve().parents[2] / 'VERSION',
    ]
    for path in candidates:
        try:
            value = path.read_text(encoding='utf-8').strip()
        except OSError:
            continue
        if value:
            return value
    return 'unknown'


def _extract_versions(payload) -> list[str]:
    """Support DockerHub tag responses and a simple {version: x.y.z} manifest."""
    if isinstance(payload, dict) and isinstance(payload.get('version'), str):
        return [payload['version']]

    versions = []
    if isinstance(payload, dict):
        for row in payload.get('results') or []:
            if isinstance(row, dict) and isinstance(row.get('name'), str):
                versions.append(row['name'])
    return versions


def _latest_version_from_remote(url: str) -> str | None:
    request = Request(
        url,
        headers={
            'Accept': 'application/json',
            'User-Agent': 'LightWMS-Version-Checker/1.0',
        },
    )
    with urlopen(request, timeout=3.0) as response:
        payload = json.loads(response.read().decode('utf-8'))

    candidates = [value for value in _extract_versions(payload) if _version_key(value)]
    if not candidates:
        return None
    return max(candidates, key=lambda value: _version_key(value) or (0, 0, 0)).lstrip('v')


def get_latest_version() -> tuple[str | None, str, str | None]:
    """Return (latest_version, source, error_message), cached to protect startup/UI."""
    override = os.getenv('LIGHTWMS_LATEST_VERSION', '').strip()
    if override:
        return override.lstrip('v'), 'environment', None

    url = os.getenv('UPDATE_CHECK_URL', DEFAULT_UPDATE_CHECK_URL).strip()
    if not url:
        return None, 'disabled', None

    try:
        interval = max(300, int(os.getenv('UPDATE_CHECK_INTERVAL_SECONDS', '1800')))
    except ValueError:
        interval = 1800

    cache_key = f'lightwms:latest-version:{url}'
    cached = cache.get(cache_key)
    if isinstance(cached, str) and cached:
        return cached, 'cache', None

    try:
        latest = _latest_version_from_remote(url)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None, 'remote', '版本检查暂不可用'

    if latest:
        cache.set(cache_key, latest, timeout=interval)
    return latest, 'remote', None


def get_version_info() -> dict:
    current = get_current_version()
    latest, source, error = get_latest_version()
    current_key = _version_key(current)
    latest_key = _version_key(latest or '')

    return {
        'current_version': current,
        'latest_version': latest,
        'update_available': bool(current_key and latest_key and latest_key > current_key),
        'source': source,
        'checked_at': timezone.now().isoformat(),
        'error': error,
    }
