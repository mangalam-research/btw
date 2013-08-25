# Django imports
from django import forms

# options to fine tune search paths
search_options = (
    (1, "BTW Library"),
    (2, "User Library"),
    (3, "Both Libraries"))


class SearchForm(forms.Form):
    """The search form """
    library = forms.ChoiceField(label='Search items from:',
                                choices=search_options)
    keyword = forms.CharField(label='Keyword:', max_length=50,)
