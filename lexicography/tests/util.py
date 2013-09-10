import logging
from StringIO import StringIO

def setup_logger_for_StringIO(logger):
    if type(logger) is str:
        logger = logging.getLogger(logger)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    return stream, handler
