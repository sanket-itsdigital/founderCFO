"""
Utility functions and mixins for automatic API access logging.
"""

import logging
from functools import wraps
from django.utils import timezone
from django.db import transaction

from dataroom.models import AccessLog

logger = logging.getLogger(__name__)


def log_api_access(request, action=None, document=None, company=None, **kwargs):
    """
    Log API access to AccessLog model.

    Args:
        request: Django request object
        action: Action type (view, download) - required for document logging
        document: Document instance (required for document logging)
        company: Company instance (optional, auto-detected from user if not provided)
        **kwargs: Additional fields to save

    Returns:
        AccessLog instance or None if logging fails
    """
    try:
        # Get user from request
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        # Auto-detect company from user if not provided
        if not company and hasattr(user, "companies"):
            company = user.companies.first()

        if not company:
            return None

        # Action is required for document logging
        if not action:
            action = AccessLog.VIEW

        # Get IP address
        ip_address = None
        if hasattr(request, "META"):
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.META.get("REMOTE_ADDR")

        # Create access log
        access_log = AccessLog.objects.create(
            company=company,
            user=user,
            document=document,
            action=action,
            ip_address=ip_address,
            timestamp=timezone.now(),
            created_by=user,
            updated_by=user,
            **kwargs,
        )

        return access_log

    except Exception as e:
        # Log error but don't break the request
        logger.error(f"Failed to log API access: {str(e)}", exc_info=True)
        return None


def log_api_access_decorator(action=None):
    """
    Decorator to automatically log API access.

    Usage:
        @log_api_access_decorator(action=AccessLog.VIEW)
        def my_view(request, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Call the original function
            response = func(request, *args, **kwargs)

            # Log the access
            log_api_access(
                request=request,
                action=action,
            )

            return response

        return wrapper

    return decorator


class AccessLogMixin:
    """
    Mixin class to automatically log API access in DRF views.

    Usage:
        class MyView(AccessLogMixin, generics.ListCreateAPIView):
            ...
    """

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to log access after response"""
        response = super().dispatch(request, *args, **kwargs)

        # Log the access (non-blocking)
        try:
            # Determine action from view type and method
            action = self._get_action_from_view(request)

            # Get document if this is a document-related view
            document = self._get_document_from_kwargs(kwargs)

            log_api_access(
                request=request,
                action=action,
                document=document,
            )
        except Exception as e:
            logger.error(f"Failed to log API access in mixin: {str(e)}", exc_info=True)

        return response

    def _get_action_from_view(self, request):
        """Determine action from view class and HTTP method"""
        # For document views, only VIEW and DOWNLOAD are supported
        view_name = self.__class__.__name__.lower()

        if "download" in view_name:
            return AccessLog.DOWNLOAD

        # Default to VIEW for document views
        return AccessLog.VIEW

    def _get_document_from_kwargs(self, kwargs):
        """Extract document from kwargs if available"""
        from dataroom.models import Document

        document_id = kwargs.get("pk") or kwargs.get("document_id") or kwargs.get("id")
        if document_id:
            try:
                return Document.objects.get(id=document_id)
            except (Document.DoesNotExist, ValueError, TypeError):
                pass
        return None
