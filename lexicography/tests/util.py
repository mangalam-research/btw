"""Testing utilities..

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import logging
from StringIO import StringIO

import lxml.etree
from pebble import process

from .. import xml
from lib import util

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

#
# What we are doing here is running the code that reads and processes
# the data necessary to create a valid document in *parallel* with the
# rest of the code. When a test actually requires the code, it
# probably will not have to wait for the read + process operation
# because it will already have been done.
#

@process.concurrent
def fetch():
    with open("utils/schemas/prasada.xml") as f:
        data = f.read().decode("utf-8")

    # Clean it for raw edit.
    data = util.run_xsltproc("utils/xsl/strip.xsl", data)

    tree = xml.XMLTree(data)
    version = tree.extract_version()

    if not util.validate(xml.schema_for_version(version),
                         data):
        raise ValueError("the file is not actually valid!")

    sch = xml.schematron_for_version(version)
    if sch and not util.schematron(sch, data):
        raise ValueError("the file does not pass schematron validation!")

    return data

fetch_task = None

def launch_fetch_task():
    """
    Calling this method will start the fetch task so that
    get_valid_document_data can return a value.
    """
    global fetch_task  # pylint: disable=global-statement
    if fetch_task is None:
        fetch_task = fetch()

def get_valid_document_data():
    if get_valid_document_data.data is not None:
        return get_valid_document_data.data

    if fetch_task is None:
        raise Exception("forgot to call launch_fetch_task")

    data = fetch_task.get()

    get_valid_document_data.data = data
    return data

get_valid_document_data.data = None
