from django import template

register = template.Library()


@register.filter
def is_editable_by(entry, user):
    return entry.is_editable_by(user)
