from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django import forms

from wed import WedWidget
from .models import Chunk


class RawSaveForm(forms.ModelForm):

    class Meta(object):
        model = Chunk
        fields = ('data', )


class SaveForm(forms.ModelForm):
    # This form is a left-over from the initial version of BTW. It has
    # ceased to act like a form a long time ago and should probably be
    # replaced with something nicer.

    class Media(object):
        js = settings.BTW_WED_POLYFILLS + \
            ((settings.BTW_REQUIREJS_PATH, )
             if not settings.BTW_WED_USE_REQUIREJS else ())

    class Meta(object):
        model = Chunk
        fields = ('data', )

    logurl = forms.CharField(widget=forms.HiddenInput(),
                             initial=reverse_lazy('lexicography_log'))
    saveurl = forms.CharField(widget=forms.HiddenInput())
    initial_etag = forms.CharField(widget=forms.HiddenInput())
    data = forms.CharField(label="",
                           widget=WedWidget(source=settings.BTW_WED_PATH,
                                            css=settings.BTW_WED_CSS))
