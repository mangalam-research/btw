from django.urls import reverse_lazy
from django.conf import settings
from django import forms

from wed import WedWidget
from .models import Chunk, Entry
from . import xml
from .xml import XMLTree


class RawSaveForm(forms.ModelForm):

    class Meta(object):
        model = Chunk
        fields = ('data', )

    _xmltree = None

    def clean_data(self):
        data = self.cleaned_data['data']
        xmltree = XMLTree(data.encode('utf-8'))
        self._xmltree = xmltree
        if self._xmltree.is_data_unclean():
            raise forms.ValidationError('The XML passed is unclean!')
        else:
            version = xmltree.extract_version_unsafe()
            if version is None:
                raise forms.ValidationError('The XML has no version!')
            elif xml.schema_for_version_unsafe(version) is None:
                raise forms.ValidationError(
                    'No schema able to handle schema version: ' + version)
            elif isinstance(xml.schematron_for_version_unsafe(version),
                            ValueError):
                raise forms.ValidationError(
                    'No schematron able to handle schema version: ' + version)
        return data

    def clean(self, *args, **kwargs):
        cleaned_data = super(RawSaveForm, self).clean(*args, **kwargs)
        xmltree = self._xmltree
        if not xmltree.is_data_unclean():
            version = xmltree.extract_version_unsafe()
            if version is not None:
                cleaned_data['schema_version'] = version
                self.instance.schema_version = version
        return cleaned_data

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
    sf_fetch_url = forms.CharField(
        widget=forms.HiddenInput(),
        initial=reverse_lazy("semantic_fields_semanticfield-list"))
    initial_etag = forms.CharField(widget=forms.HiddenInput())
    data = forms.CharField(label="",
                           widget=WedWidget(source=settings.BTW_WED_PATH,
                                            css=settings.BTW_WED_CSS))
