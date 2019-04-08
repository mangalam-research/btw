from django import forms
from django.contrib.auth import get_user_model


class SignupForm(forms.Form):

    class Meta:
        model = get_user_model()

    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
