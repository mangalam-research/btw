# Django imports
from django import forms


class SearchForm(forms.Form):
    """The search form """
    keyword = forms.CharField(label='Keyword:', max_length=50,)
