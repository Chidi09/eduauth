from fastapi import Depends
from typing import Callable

from eduauth.auth import (
    get_current_admin_user,
    get_current_teacher_or_admin_user,
    get_current_student_user,
    get_current_active_user # Also useful for any authenticated user
)
from eduauth.db_models import UserModel # Import UserModel for type hinting

# Decorator for routes that require an active authenticated user (any role)
def active_user_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to ensure that the user accessing the endpoint is authenticated and active.
    """
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        async def decorated_function(
            current_user: UserModel = Depends(get_current_active_user),
            *args: Any,
            **kwargs: Any
        ) -> Any:
            return await func(current_user=current_user, *args, **kwargs)
        return decorated_function
    return wrapper

# Decorator for routes that require an admin user
def admin_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to ensure that the user accessing the endpoint has an 'admin' role.
    """
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        async def decorated_function(
            current_user: UserModel = Depends(get_current_admin_user),
            *args: Any,
            **kwargs: Any
        ) -> Any:
            return await func(current_user=current_user, *args, **kwargs)
        return decorated_function
    return wrapper

# Decorator for routes that require a teacher or admin user
def teacher_or_admin_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to ensure that the user accessing the endpoint has a 'teacher' or 'admin' role.
    """
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        async def decorated_function(
            current_user: UserModel = Depends(get_current_teacher_or_admin_user),
            *args: Any,
            **kwargs: Any
        ) -> Any:
            return await func(current_user=current_user, *args, **kwargs)
        return decorated_function
    return wrapper

# Decorator for routes that require a student user
def student_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to ensure that the user accessing the endpoint has a 'student' role.
    """
    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        async def decorated_function(
            current_user: UserModel = Depends(get_current_student_user),
            *args: Any,
            **kwargs: Any
        ) -> Any:
            return await func(current_user=current_user, *args, **kwargs)
        return decorated_function
    return wrapper

