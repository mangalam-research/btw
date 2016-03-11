from django import forms

from . import util
from .models import SemanticField

class CategoryField(forms.IntegerField):

    def to_python(self, value):
        if value == "":
            return None

        try:
            return SemanticField.objects.get(id=value)
        except SemanticField.DoesNotExist:
            raise forms.ValidationError("There is no Category with id " +
                                        value + ".")

class SemanticFieldForm(forms.Form):

    # A ModelChoiceField might seem more convenient, as this field
    # here should contain a pk for a SemanticField. However,
    # ModelChoiceField requires a queryset from which the choice can
    # be made, and this queryset is serialized when a view using this
    # form is cached. Since all semantic fields are a priori possible
    # choices, this means a serialization that contains all semantic
    # fields!!! Using IntegerField is a simple way to avoid the
    # problem. It would also have been possible to be clever and
    # customize the form but simple is better than clever here.
    parent = CategoryField(widget=forms.HiddenInput())
    heading = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    pos = forms.ChoiceField(label="Part of speech:",
                            choices=util.POS_CHOICES_EXPANDED, initial="",
                            required=False)
