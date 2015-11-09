from django import template

register = template.Library()

@register.simple_tag
def sflink(sf, *args, **kwargs):
    return sf.make_link(*args, **kwargs)
