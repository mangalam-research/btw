import threading

from django.test import LiveServerTestCase


class SeleniumTest(LiveServerTestCase):
    def test_run(self):
        # This effectively causes the test to stop and wait for the
        # server to die.

        # Yep we call it this way to avoid the idiotic redefinition of
        # join present in django/test/testcases.py (present in version
        # 1.5, maybe 1.6)
        threading.Thread.join(self.server_thread)
