"""System settings service for LightWMS."""
import os
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from django.conf import settings as django_settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from apps.audit.models import AuditAction, AuditLog, TargetType
from ..models import SystemSettings


class SystemSettingsService:
    """Service for public branding and other system-wide settings."""

    ALLOWED_LOGO_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}
    MAX_LOGO_SIZE = 2 * 1024 * 1024
    MAX_LOGO_PIXELS = 16_777_216  # 4096 x 4096
    LOGO_UPLOAD_DIR = 'system'

    _SVG_BLOCKED_TAGS = {
        'script', 'foreignobject', 'iframe', 'object', 'embed', 'style', 'image'
    }
    _SVG_EXTERNAL_PATTERN = re.compile(
        r'(?:javascript\s*:|data\s*:|https?\s*:|url\s*\(\s*[\'\"]?\s*(?:https?\s*:|data\s*:|javascript\s*:|//))',
        re.IGNORECASE,
    )

    @classmethod
    def get_setting(cls, key: str, default: str = '') -> str:
        try:
            return SystemSettings.objects.get(key=key).value
        except SystemSettings.DoesNotExist:
            return default

    @classmethod
    @transaction.atomic
    def set_setting(
        cls,
        key: str,
        value: str,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> SystemSettings:
        """Set one key and create an immutable audit entry in the same DB transaction."""
        try:
            setting = SystemSettings.objects.select_for_update().get(key=key)
            created = False
            before_value = setting.value
            setting.value = value
            setting.updated_by = operator
            setting.save(update_fields=['value', 'updated_by', 'updated_at'])
        except SystemSettings.DoesNotExist:
            setting = SystemSettings.objects.create(
                key=key,
                value=value,
                updated_by=operator,
            )
            created = True
            before_value = None

        AuditLog.objects.create(
            action=AuditAction.CREATE if created else AuditAction.UPDATE,
            target_type=TargetType.SYSTEM,
            target_id=0,
            diff={
                'before': {'key': key, 'value': cls._audit_value(before_value)},
                'after': {'key': key, 'value': cls._audit_value(value)},
            },
            operator=operator,
            operator_role=getattr(operator, 'role', ''),
            ip=ip or None,
            user_agent=user_agent,
        )
        return setting

    @staticmethod
    def _audit_value(value):
        if value is None:
            return None
        text = str(value)
        return text[:100]

    @classmethod
    def _validate_remote_logo_url(cls, url: str) -> str:
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise ValueError('无效的 Logo URL') from exc
        if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname:
            raise ValueError('Logo URL 仅支持 http 或 https')
        if parsed.username is not None or parsed.password is not None:
            raise ValueError('Logo URL 不能包含用户名或密码')
        if any(ord(char) < 0x20 or char.isspace() for char in url):
            raise ValueError('Logo URL 包含不安全字符')
        return url

    @classmethod
    def _safe_logo_path(cls, relative_path: str) -> Optional[Path]:
        """Resolve only files below MEDIA_ROOT/system; never trust stored paths."""
        if not relative_path:
            return None
        media_root = Path(django_settings.MEDIA_ROOT).resolve()
        logo_root = (media_root / cls.LOGO_UPLOAD_DIR).resolve()
        candidate = (media_root / relative_path).resolve()
        try:
            candidate.relative_to(logo_root)
        except ValueError:
            return None
        return candidate

    @classmethod
    def _delete_logo_file(cls, relative_path: str) -> None:
        path = cls._safe_logo_path(relative_path)
        if path and path.exists() and path.is_file():
            try:
                path.unlink()
            except OSError:
                pass

    @staticmethod
    def _local_name(xml_name: str) -> str:
        return xml_name.rsplit('}', 1)[-1].lower()

    @classmethod
    def _validate_svg_bytes(cls, content: bytes) -> None:
        lowered = content.lower()
        if b'<!doctype' in lowered or b'<!entity' in lowered:
            raise ValueError('SVG 不能包含 DOCTYPE 或 ENTITY')
        try:
            root = ET.fromstring(content)
        except (ET.ParseError, ValueError) as exc:
            raise ValueError('SVG 文件无效') from exc
        if cls._local_name(root.tag) != 'svg':
            raise ValueError('文件内容不是有效 SVG')

        for element in root.iter():
            tag = cls._local_name(element.tag)
            if tag in cls._SVG_BLOCKED_TAGS:
                raise ValueError(f'SVG 包含不允许的元素: {tag}')

            for raw_name, raw_value in element.attrib.items():
                name = cls._local_name(raw_name)
                value = str(raw_value).strip()
                if name.startswith('on'):
                    raise ValueError('SVG 不能包含事件处理属性')
                if name in {'href', 'src'}:
                    lower_value = value.lower()
                    if lower_value and not lower_value.startswith('#'):
                        raise ValueError('SVG 不能引用外部资源')
                if name == 'style' and cls._SVG_EXTERNAL_PATTERN.search(value):
                    raise ValueError('SVG 样式不能引用外部或活动内容')
                if cls._SVG_EXTERNAL_PATTERN.search(value):
                    raise ValueError('SVG 属性包含不安全内容')

            if element.text and cls._SVG_EXTERNAL_PATTERN.search(element.text):
                raise ValueError('SVG 文本包含不安全内容')

    @classmethod
    def _validate_raster_file(cls, file: UploadedFile, ext: str) -> None:
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError as exc:
            raise ValueError('服务器缺少图片校验组件') from exc

        expected = {
            '.png': 'PNG',
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.webp': 'WEBP',
        }[ext]
        try:
            file.seek(0)
            image = Image.open(file)
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > cls.MAX_LOGO_PIXELS:
                raise ValueError('Logo 图片尺寸过大或无效')
            if image.format != expected:
                raise ValueError('文件扩展名与实际图片格式不匹配')
            image.verify()
        except ValueError:
            raise
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise ValueError('图片文件内容无效') from exc
        finally:
            try:
                file.seek(0)
            except Exception:
                pass

    @classmethod
    def _validate_logo_file(cls, file: UploadedFile) -> str:
        ext = os.path.splitext(file.name or '')[1].lower()
        if ext not in cls.ALLOWED_LOGO_EXTENSIONS:
            raise ValueError(
                f'不支持的文件格式。支持的格式: {", ".join(sorted(cls.ALLOWED_LOGO_EXTENSIONS))}'
            )
        if file.size <= 0:
            raise ValueError('Logo 文件不能为空')
        if file.size > cls.MAX_LOGO_SIZE:
            raise ValueError(f'文件过大。最大允许 {cls.MAX_LOGO_SIZE // 1024 // 1024}MB')

        if ext == '.svg':
            file.seek(0)
            content = file.read(cls.MAX_LOGO_SIZE + 1)
            file.seek(0)
            cls._validate_svg_bytes(content)
        else:
            cls._validate_raster_file(file, ext)
        return ext

    @classmethod
    def get_logo_url(cls) -> Optional[str]:
        logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        if logo_file and cls._safe_logo_path(logo_file):
            return f'/media/{Path(logo_file).as_posix()}'

        logo_url = cls.get_setting(SystemSettings.LOGO_URL)
        if logo_url:
            try:
                return cls._validate_remote_logo_url(logo_url)
            except ValueError:
                # A legacy or directly-corrupted value is never reflected into
                # the public login page.
                return None
        return None

    @classmethod
    def set_logo_url(
        cls,
        url: str,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> None:
        url = cls._validate_remote_logo_url(url)
        old_logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        with transaction.atomic():
            cls.set_setting(SystemSettings.LOGO_FILE, '', operator, ip, user_agent)
            cls.set_setting(SystemSettings.LOGO_URL, url, operator, ip, user_agent)
            if old_logo_file:
                transaction.on_commit(lambda p=old_logo_file: cls._delete_logo_file(p))

    @classmethod
    def upload_logo(
        cls,
        file: UploadedFile,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> str:
        """Validate content first; never delete the old logo before DB commit."""
        ext = cls._validate_logo_file(file)
        old_logo_file = cls.get_setting(SystemSettings.LOGO_FILE)

        filename = f'logo_{uuid.uuid4().hex[:8]}{ext}'
        relative_path = f'{cls.LOGO_UPLOAD_DIR}/{filename}'
        full_path = cls._safe_logo_path(relative_path)
        if full_path is None:
            raise ValueError('Logo 存储路径无效')
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file.seek(0)
            with full_path.open('wb') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            with transaction.atomic():
                cls.set_setting(
                    SystemSettings.LOGO_FILE, relative_path, operator, ip, user_agent
                )
                cls.set_setting(SystemSettings.LOGO_URL, '', operator, ip, user_agent)
                if old_logo_file and old_logo_file != relative_path:
                    transaction.on_commit(
                        lambda p=old_logo_file: cls._delete_logo_file(p)
                    )
        except Exception:
            # New file is not authoritative until both setting writes and their
            # immutable audit entries succeed.
            cls._delete_logo_file(relative_path)
            raise

        return f'/media/{relative_path}'

    @classmethod
    def clear_logo(
        cls,
        operator,
        ip: str = '',
        user_agent: str = ''
    ) -> None:
        old_logo_file = cls.get_setting(SystemSettings.LOGO_FILE)
        with transaction.atomic():
            cls.set_setting(SystemSettings.LOGO_FILE, '', operator, ip, user_agent)
            cls.set_setting(SystemSettings.LOGO_URL, '', operator, ip, user_agent)
            if old_logo_file:
                transaction.on_commit(lambda p=old_logo_file: cls._delete_logo_file(p))

    @classmethod
    def get_all_settings(cls) -> dict:
        return {'logo_url': cls.get_logo_url()}
