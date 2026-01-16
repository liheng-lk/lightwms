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
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.exceptions import TokenError

from core.exceptions import RateLimitedError


class TokenPair(NamedTuple):
    """Token pair containing access and refresh tokens."""
    access: str
    refresh: str


class AuthService:
    """
    Authentication service handling login, logout, refresh, and rate limiting.
    
    Rate limiting is implemented using Redis with IP + username dimension
    to prevent brute force attacks while avoiding NAT environment issues.
    """
    
    # Cache key prefixes
    RATE_LIMIT_KEY_PREFIX = 'login_fail:'
    RATE_LIMIT_BLOCK_KEY_PREFIX = 'login_block:'
    
    def __init__(self):
        """Initialize auth service with rate limit settings from Django settings."""
        self.rate_limit_threshold = getattr(
            settings, 'LOGIN_RATE_LIMIT_THRESHOLD', 10
        )
        self.rate_limit_window = getattr(
            settings, 'LOGIN_RATE_LIMIT_WINDOW', 300  # 5 minutes
        )
        self.rate_limit_block_ttl = getattr(
            settings, 'LOGIN_RATE_LIMIT_BLOCK_TTL', 900  # 15 minutes
        )
    
    def _get_rate_limit_key(self, ip: str, username: str) -> str:
        """
        Generate rate limit key from IP and username.
        Uses hash to normalize the key and prevent key injection.
        """
        normalized = f"{ip}:{username.lower()}"
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.RATE_LIMIT_KEY_PREFIX}{key_hash}"
    
    def _get_block_key(self, ip: str, username: str) -> str:
        """Generate block key from IP and username."""
        normalized = f"{ip}:{username.lower()}"
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.RATE_LIMIT_BLOCK_KEY_PREFIX}{key_hash}"
    
    def check_rate_limit(self, ip: str, username: str) -> None:
        """
        Check if the IP + username pair is rate limited.
        
        Raises:
            RateLimitedError: If the pair is blocked due to too many failed attempts.
        """
        block_key = self._get_block_key(ip, username)
        
        if cache.get(block_key):
            raise RateLimitedError(
                message='Too many failed login attempts. Please try again later.',
                retry_after=self.rate_limit_block_ttl
            )
    
    def _record_failed_attempt(self, ip: str, username: str) -> None:
        """
        Record a failed login attempt and block if threshold exceeded.
        """
        rate_key = self._get_rate_limit_key(ip, username)
        block_key = self._get_block_key(ip, username)
        
        # Increment failure count
        try:
            current_count = cache.get(rate_key, 0)
            new_count = current_count + 1
            cache.set(rate_key, new_count, self.rate_limit_window)
            
            # Block if threshold exceeded
            if new_count >= self.rate_limit_threshold:
                cache.set(block_key, True, self.rate_limit_block_ttl)
        except Exception:
            # If cache fails, continue without rate limiting
            pass
    
    def _clear_failed_attempts(self, ip: str, username: str) -> None:
        """Clear failed attempt counter on successful login."""
        rate_key = self._get_rate_limit_key(ip, username)
        block_key = self._get_block_key(ip, username)
        
        try:
            cache.delete(rate_key)
            cache.delete(block_key)
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
        """
        Record a login attempt in LoginLog.
        
        Args:
            username: Username attempted
            user: User object if found, None otherwise
            success: Whether login was successful
            ip: Client IP address
            user_agent: Client user agent string
        """
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
            # Don't fail login if logging fails
            pass
    
    def login(
        self,
        username: str,
        password: str,
        ip: str,
        user_agent: str
    ) -> Tuple[TokenPair, 'User']:
        """
        Authenticate user and return token pair.
        
        Args:
            username: User's username
            password: User's password
            ip: Client IP address
            user_agent: Client user agent string
        
        Returns:
            Tuple of (TokenPair, User) on success
        
        Raises:
            RateLimitedError: If rate limited
            AuthenticationFailed: If credentials are invalid
        """
        from apps.users.models import User
        from rest_framework.exceptions import AuthenticationFailed
        
        # Check rate limit before attempting authentication
        self.check_rate_limit(ip, username)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            # Record failed attempt
            self._record_failed_attempt(ip, username)
            # Log failed login
            self._log_login(username, None, False, ip, user_agent)
            raise AuthenticationFailed('Invalid username or password.')
        
        # Check if user is active
        if not user.is_active:
            self._record_failed_attempt(ip, username)
            # Log failed login (user disabled)
            self._log_login(username, user, False, ip, user_agent)
            raise AuthenticationFailed('User account is disabled.')
        
        # Clear failed attempts on successful login
        self._clear_failed_attempts(ip, username)
        
        # Log successful login
        self._log_login(username, user, True, ip, user_agent)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims
        refresh['username'] = user.username
        refresh['role'] = user.role
        
        token_pair = TokenPair(
            access=str(refresh.access_token),
            refresh=str(refresh)
        )
        
        return token_pair, user
    
    def logout(self, refresh_token: str) -> bool:
        """
        Logout user by blacklisting their refresh token.
        
        Args:
            refresh_token: The refresh token to blacklist
        
        Returns:
            True if successfully blacklisted, False otherwise
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return True
        except TokenError:
            return False
    
    def refresh(self, refresh_token: str) -> TokenPair:
        """
        Refresh tokens using a valid refresh token.
        
        Implements token rotation: issues new refresh token and blacklists old one.
        
        Args:
            refresh_token: The current refresh token
        
        Returns:
            New TokenPair with fresh access and refresh tokens
        
        Raises:
            TokenError: If refresh token is invalid or blacklisted
        """
        from apps.users.models import User
        from rest_framework_simplejwt.exceptions import InvalidToken
        
        try:
            # Parse the refresh token
            old_token = RefreshToken(refresh_token)
            
            # Get user from token
            user_id = old_token.get('user_id')
            if not user_id:
                raise InvalidToken('Token is missing user_id claim.')
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise InvalidToken('User not found.')
            
            # Check if user is active
            if not user.is_active:
                # Blacklist the token
                try:
                    old_token.blacklist()
                except Exception:
                    pass
                raise InvalidToken('User account is disabled.')
            
            # Check iat against tokens_invalid_before
            iat = old_token.get('iat')
            if iat is None:
                raise InvalidToken('Token is missing required iat claim.')
            
            try:
                token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                raise InvalidToken('Token has invalid iat claim.')
            
            if user.tokens_invalid_before:
                adjusted_invalid_before = user.tokens_invalid_before.replace(microsecond=0)
                time_diff = (adjusted_invalid_before - token_issued_at).total_seconds()
                # Allow 2 seconds clock skew
                if time_diff > 2:
                    raise InvalidToken('Token has been invalidated.')
            
            # Blacklist old token (rotation)
            old_token.blacklist()
            
            # Generate new tokens
            new_refresh = RefreshToken.for_user(user)
            new_refresh['username'] = user.username
            new_refresh['role'] = user.role
            
            return TokenPair(
                access=str(new_refresh.access_token),
                refresh=str(new_refresh)
            )
            
        except TokenError as e:
            raise InvalidToken(str(e))
    
    def blacklist_all_user_tokens(self, user: 'User') -> int:
        """
        Blacklist all outstanding tokens for a user.
        
        This is called when disabling a user to ensure all their tokens
        become invalid immediately.
        
        Args:
            user: The user whose tokens should be blacklisted
        
        Returns:
            Number of tokens blacklisted
        """
        count = 0
        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        
        for token in outstanding_tokens:
            # Check if already blacklisted
            if not BlacklistedToken.objects.filter(token=token).exists():
                BlacklistedToken.objects.create(token=token)
                count += 1
        
        return count
