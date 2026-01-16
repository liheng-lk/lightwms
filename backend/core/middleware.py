"""
Custom middleware for LightWMS.
"""


class RequestContextMiddleware:
    """
    Middleware to extract and attach client IP and User-Agent to request.
    Handles X-Forwarded-For and X-Real-IP headers for reverse proxy setups.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract client IP
        request.client_ip = self.get_client_ip(request)
        
        # Extract User-Agent
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        """
        Get the real client IP address.
        Checks X-Forwarded-For and X-Real-IP headers first (for reverse proxy),
        then falls back to REMOTE_ADDR.
        """
        # Check X-Forwarded-For header (may contain multiple IPs)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the list (original client)
            return x_forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        
        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '')
