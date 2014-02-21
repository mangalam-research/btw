from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from .models import Invitation
from django.shortcuts import render


class AccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        invitation_key = request.session.get('invitation_key', False)
        if invitation_key:
            invitation = Invitation.objects.get_active_invitation(
                invitation_key)

            if invitation:
                return True

        raise ImmediateHttpResponse(
            render(request,
                   'invitation/wrong_invitation_key.html'))
