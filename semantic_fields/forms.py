from django import forms

from . import util

class SemanticFieldForm(forms.Form):

    heading = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    pos = forms.ChoiceField(label="Part of speech:",
                            choices=util.POS_CHOICES_EXPANDED, initial="",
                            required=False)
