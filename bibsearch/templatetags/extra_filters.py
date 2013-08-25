# django imports
from django import template

register = template.Library()


@register.filter(name='authorToString')
def convert(list_obj):
    """ concatenates the name of the authors if found """
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
    """ actual function that can filter the extras dict """
    try:
        if key_string in dict_obj:
            return dict_obj[key_string].get(attribute_string)
    except TypeError:
        return ""


@register.filter(name='toLibrary')
def filterdict(dict_obj, key_string):
    """ returns the object_type from extras dict """
    return parsedict(dict_obj, key_string, 'object_type')


@register.filter(name='toCopyStatus')
def filterdict(dict_obj, key_string):
    """ returns the sync_status from extras dict """
    return parsedict(dict_obj, key_string, 'sync_status')


@register.filter(name='toPubDate')
def filterdict(dict_obj, key_string):
    """ returns the pub_date from extras dict """
    return parsedict(dict_obj, key_string, 'pub_date')
