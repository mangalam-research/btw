from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.models import Site
from django.dispatch import receiver
from django.views.decorators.cache import never_cache

from allauth.account.signals import user_signed_up

from .forms import InvitationForm
from .models import Invitation


def _send(request, invitation, note):
    site = Site.objects.get_current()
    subject = "Invitation to register on " + site.name + "."
    context = {
        'sender_note': note,
        'site': site,
        'expiration_days': settings.INVITATION_EXPIRY_DAYS,
        'link': request.build_absolute_uri(
            reverse('invitation_use',
                    kwargs={'key': invitation.key}))
    }
    message = render_to_string('invitation/invitation_email.txt', context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
              [invitation.recipient])

@never_cache
@login_required
@permission_required('invitation.add_invitation', raise_exception=True)
def invite(request):
    if request.method == 'POST':
        form = InvitationForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            invitation = Invitation.objects.create_invitation(
                recipient=form.cleaned_data["email"])
            _send(request, invitation, form.cleaned_data["sender_note"])
            return HttpResponseRedirect(reverse('invitation_complete'))
    else:
        form = InvitationForm()

    return render(request, "invitation/invite.html", {"form": form})


@never_cache
def use(request, key):
    invitation = Invitation.objects.get_active_invitation(key)

    if invitation:
        request.session['invitation_key'] = key
        return HttpResponseRedirect(reverse("account_signup"))

    return render(request, "invitation/wrong_invitation_key.html")


@receiver(user_signed_up)
def signed_up(sender, **kwargs):
    request = kwargs['request']
    if 'invitation_key' in request.session:
        invitation = None
        try:
            invitation = Invitation.objects.get(
                key=request.session['invitation_key'])
        except Invitation.DoesNotExist:
            # We do not plan to keep expired keys indefinitely. So
            # this is not likely but **could** happen if the user
            # used the key just before expiration, left the
            # browser open, and the key was garbage collected
            # because it is expired.
            pass

        if invitation:
            invitation.used = True
            invitation.save()

        del request.session['invitation_key']
