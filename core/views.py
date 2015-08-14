import datetime

from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.contrib.auth import logout as auth_logout
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.shortcuts import render

import lib.util as util

def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("pages-root"))

@require_GET
@never_cache
def mods(request):
    access_date = request.GET.get('access-date', None)
    if access_date is None:
        return HttpResponseBadRequest(
            "access-date is a required parameter")

    return render(request,
                  "core/mods.xml",
                  {
                      'version': util.version(),
                      'year': '2012-' + str(datetime.date.today().year),
                      'access_date': access_date,
                  },
                  content_type="application/xml+mods")
