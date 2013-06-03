from __future__ import unicode_literals
from django import forms
from django.forms.util import flatatt
from django.utils.safestring import mark_safe


class WedWidget(forms.Widget):
    def __init__(self, source, css=[], require=None, *args, **kwargs):
        if css is None:
            css = []
        else:
            css = list(css) if isinstance(css, (tuple, list)) else [css]

        js = list(source) if isinstance(source, (list, tuple)) \
            else [source] if source is not None else []

        js.append("wed/widget.js")
        
        css = { "screen": css }

        self._media = forms.Media(js=js, css=css)
        super(WedWidget, self).__init__(*args, **kwargs)

    @property
    def media(self):
        return self._media

    def render(self, name, value, attrs=None):
        attrs = attrs or self.attrs

        wed_attrs = {
            "class": "wed-widget loading",
            "id": attrs['id']
        }
        return mark_safe('<div%s>%s</div>' % (flatatt(wed_attrs), value))

    def __unicode__(self):
        return self.render()
