from django import forms

from . import util

class SemanticFieldForm(forms.Form):

    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        possible_poses = kwargs.pop('possible_poses', None)
        super(SemanticFieldForm, self).__init__(*args, **kwargs)
        self.title = title
        pos_choices = util.POS_CHOICES_EXPANDED if possible_poses is None \
            else \
            (x for x in util.POS_CHOICES_EXPANDED if x[0] in possible_poses)
        self.fields['pos'] = \
            forms.ChoiceField(label="Part of speech:",
                              choices=pos_choices, initial="",
                              required=False)

    heading = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
