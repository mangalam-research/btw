from django import forms
from .models import PrimarySource


class PrimarySourceForm(forms.ModelForm):

    class Meta(object):
        model = PrimarySource
        fields = ('item', 'reference_title', 'genre')
        widgets = {
            'item': forms.HiddenInput(),
            'reference_title': forms.Textarea(attrs={'rows': 2})
        }
