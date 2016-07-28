from django.views.generic import TemplateView

class ContextTemplateView(TemplateView):
    context = None

    def get_context_data(self, **kwargs):
        context = super(ContextTemplateView, self).get_context_data(**kwargs)
        if self.context is not None:
            context.update(self.context)
        return context
