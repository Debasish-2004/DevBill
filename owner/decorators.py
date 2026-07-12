from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.contrib import messages
from django.shortcuts import redirect


def is_owner(user):
    return user.is_authenticated and user.is_active and not user.is_staff


def owner_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_active:
            return redirect_to_login(request.get_full_path(), login_url='owner_login')
        if user.is_staff:
            messages.error(
                request,
                'Staff accounts cannot access the owner portal. Use the admin panel instead.',
            )
            return redirect('owner_login')
        return view_func(request, *args, **kwargs)

    return _wrapped
