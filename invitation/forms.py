from django import forms


class InvitationForm(forms.Form):
    email = forms.EmailField()
    sender_note = forms.CharField(
        widget=forms.Textarea, required=False, label='Your Note')
