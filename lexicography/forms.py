from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django import forms

from wed import WedWidget
from .models import Chunk


class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search")


class RawSaveForm(forms.ModelForm):
    class Meta(object):
        model = Chunk
        exclude = ('c_hash', 'is_normal')


class SaveForm(forms.ModelForm):
    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH, ) \
            if not settings.BTW_WED_USE_REQUIREJS else ()

    class Meta(object):
        model = Chunk
        exclude = ('c_hash', 'is_normal')

    logurl = forms.CharField(widget=forms.HiddenInput(),
                             initial=reverse_lazy('lexicography_log'))
    saveurl = forms.CharField(widget=forms.HiddenInput())
    data = forms.CharField(label="",
                           widget=WedWidget(source=settings.BTW_WED_PATH,
                                            css=settings.BTW_WED_CSS))
