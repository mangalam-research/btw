class XQueryBuilder(object):

    xquery_version = "3.0"
    xquery_version_declaration = "xquery version '{xquery_version}';"
    btw_namespace = "http://mangalamresearch.org/ns/btw-storage"
    btw_namespace_declaration = "declare namespace btw = '{btw_namespace}';"

    def make(self, query):
        btw_namespace_declaration = \
            self.btw_namespace_declaration.format(
                btw_namespace=self.btw_namespace)

        xquery_version_declaration = \
            self.xquery_version_declaration.format(
                xquery_version=self.xquery_version)

        ret = "\n".join((xquery_version_declaration,
                         btw_namespace_declaration, query))
        return ret

    @staticmethod
    def format_value(value):
        if isinstance(value, FormattingObject):
            return value.value

        return "".join(['"' + value.replace('"', '&#34;') + '"'])

    def format(self, query, **kwargs):
        return self.make(query.format(
            **{key: self.format_value(value) for (key, value)
               in kwargs.items()}))

class FormattingObject(object):

    def __init__(self, value):
        self.value = value

class Verbatim(FormattingObject):
    pass

default_builder = XQueryBuilder()

def make(query):
    return default_builder.make(query)

def format(query, **kwargs):
    return default_builder.format(query, **kwargs)
