# django imports
from django import template

register = template.Library()


@register.filter
def authors(list_obj):
    """Concatenates the name of the authors if found."""
    author_list = []
    for each in list_obj:
        try:
            if 'creatorType' in each and each['creatorType'] == 'author':
                if 'name' in each:
                    author_name = each['name']
                else:
                    author_name = each["firstName"] + " " + each["lastName"]
                author_list.append(author_name)
        except KeyError:
            pass
    return ", ".join(author_list)


def parsedict(dict_obj, key_string, attribute_string):
    """Actual function that can filter the extras dict."""
    try:
        if key_string in dict_obj:
            return dict_obj[key_string].get(attribute_string)
    except TypeError:
        return ""


@register.filter
def library(dict_obj, key_string):
    """Returns the object_type from extra data dictionary."""
    return parsedict(dict_obj, key_string, 'object_type')


@register.filter
def copy_status(dict_obj, key_string):
    """Returns the sync_status from extra data dictionary."""
    return parsedict(dict_obj, key_string, 'sync_status')
