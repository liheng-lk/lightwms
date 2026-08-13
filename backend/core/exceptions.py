"""
Custom exception classes and exception handler for LightWMS.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from django.db import IntegrityError

logger = logging.getLogger(__name__)

# Error code constants for semantic mapping
DUPLICATE_SKU = 'DUPLICATE_SKU'
DUPLICATE_BARCODE = 'DUPLICATE_BARCODE'
ITEM_ALREADY_BORROWED = 'ITEM_ALREADY_BORROWED'
CONCURRENT_CONFLICT = 'CONCURRENT_CONFLICT'
INTEGRITY_ERROR = 'INTEGRITY_ERROR'


class BusinessConflictError(APIException):
    """Exception for business logic conflicts (409)."""
    
    status_code = 409
    default_code = 'conflict'
    default_detail = 'Business conflict occurred.'
    
    def __init__(self, code=None, message=None, details=None):
        self.code = code or self.default_code
        self.message = message or self.default_detail
        self.details = details
        super().__init__(detail=self.message)


class RateLimitedError(APIException):
    """Exception for rate limiting (429)."""
    
    status_code = 429
    default_code = 'AUTH_RATE_LIMITED'
    default_detail = 'Too many requests. Please try again later.'
    
    def __init__(self, message=None, retry_after=None):
        self.message = message or self.default_detail
        self.retry_after = retry_after
        super().__init__(detail=self.message)


# Constraint name to error code mapping. Keep both the explicit migration
# constraint and Django's field-level unique constraint name because existing
# installations may contain either form.
CONSTRAINT_ERROR_MAP = {
    'uq_item_sku': DUPLICATE_SKU,
    'inventory_item_sku_key': DUPLICATE_SKU,
    'uq_item_barcode_not_null': DUPLICATE_BARCODE,
    'uq_borrow_active_item': ITEM_ALREADY_BORROWED,
}


def custom_exception_handler(exc, context):
    """
    Custom exception handler that:
    1. Handles BusinessConflictError and RateLimitedError
    2. Maps IntegrityError to 409 based on constraint name
    3. Returns consistent error format: {code, message, details}
    """
    # Handle IntegrityError from database constraints
    if isinstance(exc, IntegrityError):
        return handle_integrity_error(exc, context)
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Format the response consistently
        error_data = format_error_response(exc, response)
        response.data = error_data
    
    return response


def handle_integrity_error(exc, context):
    """
    Handle IntegrityError by mapping constraint names to semantic error codes.
    Falls back to generic INTEGRITY_ERROR if constraint is unknown.
    """
    constraint_name = None
    error_code = INTEGRITY_ERROR
    
    # Try to extract constraint name from the exception
    if hasattr(exc, '__cause__') and exc.__cause__:
        cause = exc.__cause__
        if hasattr(cause, 'diag') and hasattr(cause.diag, 'constraint_name'):
            constraint_name = cause.diag.constraint_name
    
    # Map constraint name to error code
    if constraint_name and constraint_name in CONSTRAINT_ERROR_MAP:
        error_code = CONSTRAINT_ERROR_MAP[constraint_name]
    
    # Log the error for debugging
    logger.warning(
        f"IntegrityError caught: constraint={constraint_name}, "
        f"mapped_code={error_code}, original={str(exc)}"
    )
    
    # Build error message based on error code
    messages = {
        DUPLICATE_SKU: 'An item with this SKU already exists.',
        DUPLICATE_BARCODE: 'An item with this barcode already exists.',
        ITEM_ALREADY_BORROWED: 'This item is already borrowed.',
        CONCURRENT_CONFLICT: 'Concurrent modification conflict.',
        INTEGRITY_ERROR: 'Database constraint violation.',
    }
    
    return Response(
        {
            'code': error_code,
            'message': messages.get(error_code, 'Database constraint violation.'),
            'details': {'constraint': constraint_name} if constraint_name else None,
        },
        status=409
    )


def format_error_response(exc, response):
    """Format exception into consistent error response structure."""
    code = getattr(exc, 'code', None) or getattr(exc, 'default_code', 'error')
    message = getattr(exc, 'message', None) or str(exc.detail) if hasattr(exc, 'detail') else str(exc)
    details = getattr(exc, 'details', None)
    
    # Handle DRF's detail format (can be string, list, or dict)
    if hasattr(exc, 'detail'):
        detail = exc.detail
        if isinstance(detail, dict):
            details = detail
            message = 'Validation error.'
        elif isinstance(detail, list):
            details = {'errors': detail}
            message = detail[0] if detail else 'Validation error.'
        else:
            message = str(detail)
    
    return {
        'code': code,
        'message': message,
        'details': details,
    }
