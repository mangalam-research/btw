"""Testing utilities..

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import logging
from StringIO import StringIO

import lxml.etree

from .. import xml


def setup_logger_for_StringIO(logger):
    """
Add a :class:`logging.StreamHandler` to the logger so that it
outputs to a :class:`StringIO` object.

:param logger: The logger to manipulate.

:type logger: :class:`str` or :class:`logging.Logger`.

:return: The StringIO object and the handler that were created.

:rtype: (:class:`StringIO`, :class:`logging.StreamHandler`)
"""
    if type(logger) is str:
        logger = logging.getLogger(logger)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    return stream, handler


def parse_response_to_wed(json_response):
    """
Convert a json response to a Python dictionary.

:param json_response: The response obtained from the server in JSON format.

:type json_response: :class:`str`

:returns: A dictionary that contains one key per message type that was
          encountered. Each key is associated with an array that
          contains the messages of that type.

:rtype: :class:`dict`
"""
    if "messages" not in json_response:
        raise ValueError("response does not have a messages field")
    messages = json_response["messages"]

    ret = {}
    for message in messages:
        array = ret.setdefault(message["type"], [])
        array.append(message)

    return ret


def stringify_etree(data):
    # This forces empty elements to be output as <foo></foo>
    # rather than <foo/> so that it is consistent with how wed
    # handles data.
    for el in data.iter():
        if len(el) == 0 and el.text is None:
            el.text = ''

    return lxml.etree.tostring(data)


def set_lemma(data, new_lemma):
    data = xml.xhtml_to_xml(data).encode("utf-8")

    data_tree = lxml.etree.fromstring(data)

    # This casts a wider net than strictly necessary but it does not
    # matter.
    lemma_hits = data_tree.xpath(
        "btw:lemma",
        namespaces={'btw': 'http://mangalamresearch.org/ns/btw-storage'})

    for lemma in lemma_hits:
        if new_lemma is None:  # None means "remove the lemma"
            lemma.getparent().remove(lemma)
        else:
            del lemma[:]
            lemma.text = new_lemma

    return data_tree
