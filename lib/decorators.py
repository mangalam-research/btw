from functools import wraps

from django.utils.decorators import available_attrs

def wed_hack(view_func):
    """
    Marks a view function as requiring the wed hack.
    """
    # We could just do view_func.needs_wed_hack = True, but decorators
    # are nicer if they don't have side-effects, so we return a new
    # function.
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)
    wrapped_view.needs_wed_hack = True
    return wraps(view_func, assigned=available_attrs(view_func))(wrapped_view)
