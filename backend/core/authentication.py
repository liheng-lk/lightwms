"""
Custom JWT authentication for LightWMS.
"""
from datetime import datetime, timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that:
    1. Requires 'iat' claim in token (missing = invalid)
    2. Checks token iat against user.tokens_invalid_before
    3. Verifies user.is_active
    """
    
    def get_user(self, validated_token):
        """
        Get user and validate token against tokens_invalid_before.
        """
        user = super().get_user(validated_token)
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationFailed('User account is disabled.')
        
        # Get iat claim (issued at)
        iat = validated_token.get('iat')
        if iat is None:
            raise InvalidToken('Token is missing required iat claim.')
        
        # Convert iat to datetime (aware, UTC)
        try:
            token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            raise InvalidToken('Token has invalid iat claim.')
        
        # Check against tokens_invalid_before if set
        tokens_invalid_before = getattr(user, 'tokens_invalid_before', None)
        if tokens_invalid_before:
            # Allow 2 seconds clock skew to avoid edge case issues
            clock_skew_seconds = 2
            adjusted_invalid_before = tokens_invalid_before.replace(microsecond=0)
            
            # Token must be issued after tokens_invalid_before (with skew tolerance)
            if token_issued_at < adjusted_invalid_before:
                # Check if within clock skew tolerance
                time_diff = (adjusted_invalid_before - token_issued_at).total_seconds()
                if time_diff > clock_skew_seconds:
                    raise InvalidToken('Token has been invalidated.')
        
        return user
