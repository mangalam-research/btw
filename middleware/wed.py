from django.utils.deprecation import MiddlewareMixin

class WedHack(MiddlewareMixin):
    """
    This is a middleware used to work around a bug in wed 0.29 and
    earlier. The problem is that wed will issue an If-Match header
    with the value "" when it does not want a check to be
    performed. It used to work on earlier versions of Django because
    Django's earlier logic accepted "" as meaning "don't
    check".

    This middleware needs to be turned on on a view-by-view basis
    using a decorator in ``lib.decorators``. This way we don't risk
    masking issues that could arise from other sources. [Actually, no,
    please read the comments in the source.]
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        #
        # **Huge sigh**... ideally this would not be commented out but
        # it is. The problem is that django-cms has a decorator that
        # blasts away our flag because its cms_perms decorator is
        # awfully implemented. We'll have to take our chances with
        # making this fix global and perhaps hiding problems from
        # other sources.
        #
        # If the view was not marked with the flag that turns on this
        # middleware, don't do anything.
        # import inspect
        # print("XXX",
        #     getattr(view_func, "needs_wed_hack", None), view_func.__name__)
        # print("XXX2", inspect.getsourcelines(view_func))
        # if not getattr(view_func, "needs_wed_hack", None):
        #     return None

        match = request.META.get("HTTP_IF_MATCH", None)
        if match is not None:
            if match == '""':
                del request.META["HTTP_IF_MATCH"]

        return None
