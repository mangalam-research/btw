import re

from django.test import TestCase
from django.core.management.base import SystemCheckError
from django.core.management import call_command

class CheckTestCase(TestCase):

    def test_no_error(self):
        """
        Tests that there is no error reported by default.
        """
        # Check raises an exception if it fails, no need to check stdout
        # and stderr.
        call_command("check")

    def test_no_csrf_cookie_httponly(self):
        """
        Tests that CSRF_COOKIE_HTTPONLY cannot be True.
        """
        with self.settings(CSRF_COOKIE_HTTPONLY=True):
            with self.assertRaisesRegex(SystemCheckError, re.escape("""\
SystemCheckError: System check identified some issues:

ERRORS:
?: (core.E001) BTW cannot work with CSRF_COOKIE_HTTPONLY set to True. It \
only makes attacks somewhat harder, whereas the BTW's JavaScript code needs \
to get the CSRF token, and getting it from a cookie is the easiest way.

System check identified 1 issue (0 silenced).""")):
                call_command("check", "--no-color")
