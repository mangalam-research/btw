"""Testing utilities..

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import logging
from StringIO import StringIO


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
