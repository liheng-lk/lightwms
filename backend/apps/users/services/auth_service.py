"""
Authentication service for LightWMS.
Handles login, logout, token refresh, and rate limiting.
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple, NamedTuple

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from core.exceptions import RateLimitedError


class TokenPair(NamedTuple):
    access: str
    refresh: str


class AuthService:
    """Authentication service with rate limits and one-time refresh rotation."""

    RATE_LIMIT_KEY_PREFIX = 'login_fail:'
    RATE_LIMIT_BLOCK_KEY_PREFIX = 'login_block:'

    def __init__(self):
        self.rate_limit_threshold = getattr(settings, 'LOGIN_RATE_LIMIT_THRESHOLD', 10)
        self.rate_limit_window = getattr(settings, 'LOGIN_RATE_LIMIT_WINDOW', 300)
        self.rate_limit_block_ttl = getattr(settings, 'LOGIN_RATE_LIMIT_BLOCK_TTL', 900)

    def _get_rate_limit_key(self, ip: str, username: str) -> str:
        normalized = f"{ip}:{username.lower()}"
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.RATE_LIMIT_KEY_PREFIX}{key_hash}"

    def _get_block_key(self, ip: str, username: str) -> str:
        normalized = f"{ip}:{username.lower()}"
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.RATE_LIMIT_BLOCK_KEY_PREFIX}{key_hash}"

    def check_rate_limit(self, ip: str, username: str) -> None:
        if cache.get(self._get_block_key(ip, username)):
            raise RateLimitedError(
                message='Too many failed login attempts. Please try again later.',
                retry_after=self.rate_limit_block_ttl
            )

    def _record_failed_attempt(self, ip: str, username: str) -> None:
        rate_key = self._get_rate_limit_key(ip, username)
        block_key = self._get_block_key(ip, username)
        try:
            if cache.add(rate_key, 1, self.rate_limit_window):
                new_count = 1
            else:
                try:
                    new_count = cache.incr(rate_key)
                except ValueError:
                    cache.set(rate_key, 1, self.rate_limit_window)
                    new_count = 1
            if new_count >= self.rate_limit_threshold:
                cache.set(block_key, True, self.rate_limit_block_ttl)
        except Exception:
            pass

    def _clear_failed_attempts(self, ip: str, username: str) -> None:
        try:
            cache.delete(self._get_rate_limit_key(ip, username))
            cache.delete(self._get_block_key(ip, username))
        except Exception:
            pass

    def _log_login(
        self,
        username: str,
        user: Optional['User'],
        success: bool,
        ip: str,
        user_agent: str
    ) -> None:
        from apps.audit.models import LoginLog
        try:
            LoginLog.objects.create(
                username_attempted=username,
                user=user,
                success=success,
                ip=ip,
                user_agent=user_agent or ''
            )
        except Exception:
            pass

    def login(
        self,
        username: str,
        password: str,
        ip: str,
        user_agent: str
    ) -> Tuple[TokenPair, 'User']:
        from rest_framework.exceptions import AuthenticationFailed

        self.check_rate_limit(ip, username)
        user = authenticate(username=username, password=password)

        if user is None:
            self._record_failed_attempt(ip, username)
            self._log_login(username, None, False, ip, user_agent)
            raise AuthenticationFailed('Invalid username or password.')

        if not user.is_active:
            self._record_failed_attempt(ip, username)
            self._log_login(username, user, False, ip, user_agent)
            raise AuthenticationFailed('User account is disabled.')

        self._clear_failed_attempts(ip, username)
        self._log_login(username, user, True, ip, user_agent)

        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.username
        refresh['role'] = user.role
        return TokenPair(access=str(refresh.access_token), refresh=str(refresh)), user

    def _parse_refresh(self, refresh_token: str) -> RefreshToken:
        try:
            return RefreshToken(refresh_token)
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

    def _locked_outstanding(self, token: RefreshToken) -> OutstandingToken:
        jti = token.get('jti')
        if not jti:
            raise InvalidToken('Token is missing jti claim.')
        try:
            return (
                OutstandingToken.objects.select_for_update()
                .select_related('user')
                .get(jti=jti)
            )
        except OutstandingToken.DoesNotExist as exc:
            raise InvalidToken('Refresh token is not outstanding.') from exc

    @staticmethod
    def _blacklist_locked(outstanding: OutstandingToken) -> None:
        if BlacklistedToken.objects.filter(token=outstanding).exists():
            raise InvalidToken('Token is blacklisted.')
        try:
            BlacklistedToken.objects.create(token=outstanding)
        except IntegrityError as exc:
            raise InvalidToken('Token is blacklisted.') from exc

    def logout(self, refresh_token: str, expected_user=None) -> bool:
        """Blacklist one refresh token, optionally enforcing its owner."""
        try:
            token = self._parse_refresh(refresh_token)
            token_user_id = token.get('user_id')
            if not token_user_id:
                raise InvalidToken('Token is missing user_id claim.')
            if expected_user is not None and int(token_user_id) != int(expected_user.id):
                raise PermissionDenied('Refresh token belongs to another user.')

            with transaction.atomic():
                outstanding = self._locked_outstanding(token)
                if outstanding.user_id != int(token_user_id):
                    raise InvalidToken('Refresh token owner mismatch.')
                if expected_user is not None and outstanding.user_id != expected_user.id:
                    raise PermissionDenied('Refresh token belongs to another user.')
                self._blacklist_locked(outstanding)
            return True
        except PermissionDenied:
            raise
        except (InvalidToken, TokenError, ValueError, TypeError):
            return False

    def refresh(self, refresh_token: str) -> TokenPair:
        """Atomically consume a refresh token and rotate it exactly once."""
        from apps.users.models import User

        old_token = self._parse_refresh(refresh_token)
        user_id = old_token.get('user_id')
        if not user_id:
            raise InvalidToken('Token is missing user_id claim.')

        invalid_message = None
        token_pair = None

        with transaction.atomic():
            outstanding = self._locked_outstanding(old_token)
            if outstanding.user_id != int(user_id):
                raise InvalidToken('Refresh token owner mismatch.')
            if BlacklistedToken.objects.filter(token=outstanding).exists():
                raise InvalidToken('Token is blacklisted.')

            try:
                user = User.objects.select_for_update().get(id=user_id)
            except User.DoesNotExist as exc:
                raise InvalidToken('User not found.') from exc

            if not user.is_active:
                self._blacklist_locked(outstanding)
                invalid_message = 'User account is disabled.'
            else:
                iat = old_token.get('iat')
                if iat is None:
                    self._blacklist_locked(outstanding)
                    invalid_message = 'Token is missing required iat claim.'
                else:
                    try:
                        token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
                    except (ValueError, TypeError, OSError):
                        self._blacklist_locked(outstanding)
                        invalid_message = 'Token has invalid iat claim.'
                    else:
                        if user.tokens_invalid_before:
                            adjusted_invalid_before = user.tokens_invalid_before.replace(microsecond=0)
                            time_diff = (adjusted_invalid_before - token_issued_at).total_seconds()
                            if time_diff > 2:
                                self._blacklist_locked(outstanding)
                                invalid_message = 'Token has been invalidated.'

                if invalid_message is None:
                    self._blacklist_locked(outstanding)
                    new_refresh = RefreshToken.for_user(user)
                    new_refresh['username'] = user.username
                    new_refresh['role'] = user.role
                    token_pair = TokenPair(
                        access=str(new_refresh.access_token),
                        refresh=str(new_refresh)
                    )

        # Raise only after the transaction commits so an invalid/disabled
        # refresh stays blacklisted even if the account is later re-enabled.
        if invalid_message is not None:
            raise InvalidToken(invalid_message)
        return token_pair

    def blacklist_all_user_tokens(self, user: 'User') -> int:
        count = 0
        with transaction.atomic():
            outstanding_tokens = list(
                OutstandingToken.objects.select_for_update().filter(user=user)
            )
            for token in outstanding_tokens:
                if not BlacklistedToken.objects.filter(token=token).exists():
                    BlacklistedToken.objects.create(token=token)
                    count += 1
        return count
