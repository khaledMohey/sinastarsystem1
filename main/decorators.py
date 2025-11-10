# utils.py
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")  # لو مش مسجل دخول
            if hasattr(request.user, "profile") and request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied  # لو مش مسموحله
        return _wrapped_view
    return decorator
