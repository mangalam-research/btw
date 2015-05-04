from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import logout as auth_logout


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("pages-root"))
