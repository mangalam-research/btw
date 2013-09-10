"""Testing utilities..

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import logging
from StringIO import StringIO

def setup_logger_for_StringIO(logger):
    """
Add a :class:`logging.StreamHandler` to he logger so that it outputs
to a :class:`StringIO` object.

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
