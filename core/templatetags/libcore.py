from django import template
from lib import util

register = template.Library()


@register.filter
def nice_name(user):
    return util.nice_name(user)
