# pylint: disable=W0401,W0614

import os
from lib.settings import s

s.BTW_SELENIUM_TESTS = True

from . import test_settings  # noqa, pylint: disable=unused-import

globals().update(s.as_dict())
