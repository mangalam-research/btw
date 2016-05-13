from django import forms

from . import util

class SemanticFieldForm(forms.Form):

    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        possible_poses = kwargs.pop('possible_poses', None)
        class_prefix = kwargs.pop('class_prefix', None)
        submit_text = kwargs.pop('submit_text', "Submit")

        super(SemanticFieldForm, self).__init__(*args, **kwargs)

        self.title = title
        self.class_prefix = class_prefix
        self.submit_text = submit_text
        pos_choices = util.POS_CHOICES_EXPANDED if possible_poses is None \
            else \
            set(x for x in util.POS_CHOICES_EXPANDED if x[0] in possible_poses)

        if len(pos_choices) != 0:
            self.fields['pos'] = \
                forms.ChoiceField(label="Part of speech:",
                                  choices=pos_choices, initial="",
                                  required=False)

    heading = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
