from django import template
from django.template.base import TextNode
from lib import util

register = template.Library()


@register.filter
def nice_name(user):
    return util.nice_name(user)


@register.tag(name="version")
def version(parser, token):
    return TextNode(util.version())
