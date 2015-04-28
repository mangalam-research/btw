from __future__ import unicode_literals
from django import forms
from django.forms.utils import flatatt
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

        css = {"screen": css}

        self._media = forms.Media(js=js, css=css)
        super(WedWidget, self).__init__(*args, **kwargs)

    @property
    def media(self):
        return self._media

    def render(self, name, value, attrs=None):
        attrs = attrs or self.attrs

        parent_attrs = {
            "class": "wed-widget-parent",
        }
        wed_attrs = {
            "class": "wed-widget loading container",
            "style": "display: none",
        }
        script_attrs = {
            "id": attrs['id'],
            "type": "text/xml"
        }
        return mark_safe(
            '<div%s><div>Loading...</div><div%s></div>'
            '<script%s>%s</script></div>' %
            (flatatt(parent_attrs), flatatt(wed_attrs), flatatt(script_attrs),
             value))

    def __unicode__(self):
        return self.render()
