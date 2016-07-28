from django.views.generic import TemplateView

class ContextTemplateView(TemplateView):
    """
    A template view that allows passing custom context to the view.
    """
    context = None

    def get_context_data(self, **kwargs):
        context = super(ContextTemplateView, self).get_context_data(**kwargs)
        if self.context is not None:
            context.update(self.context)
        return context
