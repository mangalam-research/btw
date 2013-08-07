from mixins import LoginRequiredMixin

from django.views.generic.edit import CreateView, UpdateView

class LoginRequiredCreateView(LoginRequiredMixin, CreateView):
    pass

class LoginRequiredUpdateView(LoginRequiredMixin, UpdateView):
    pass
