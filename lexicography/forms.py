from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django import forms

from wed import WedWidget
from .models import Chunk


class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search for:")
    headwords_only = forms.BooleanField(label="Headwords only",
                                        required=False)


class RawSaveForm(forms.ModelForm):
    editable_format = forms.BooleanField(
        label=("Data entered in the editable format (XHTML) rather than "
               "the btw-storage format (XML)."), required=False)

    class Meta(object):
        model = Chunk
        fields = ('data', )


class SaveForm(forms.ModelForm):

    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH, ) \
            if not settings.BTW_WED_USE_REQUIREJS else ()

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
