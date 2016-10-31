from django import forms
from .models import PrimarySource


class PrimarySourceForm(forms.ModelForm):
    reference_title = forms.CharField(strip=False,
                                      widget=forms.Textarea(attrs={'rows': 2}))

    class Meta(object):
        model = PrimarySource
        fields = ('item', 'reference_title', 'genre')
        widgets = {
            'item': forms.HiddenInput(),
        }
