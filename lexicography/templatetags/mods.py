from django import template

register = template.Library()


@register.inclusion_tag('lexicography/mods_names.xml')
def mods_names(names, marcrelator):
    if not isinstance(names, list):
        raise ValueError("names must be a list")

    if not isinstance(marcrelator, unicode):
        raise ValueError("marcrelator must be a string")
    return {'names': names, 'marcrelator': marcrelator}
