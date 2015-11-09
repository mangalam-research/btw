from django import forms

from . import util
from .models import Category

class CategoryForm(forms.Form):

    parent = forms.ModelChoiceField(
        queryset=Category.objects.all(), widget=forms.HiddenInput())
    heading = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    pos = forms.ChoiceField(label="Part of speech:",
                            choices=util.POS_CHOICES_EXPANDED, initial="",
                            required=False)
