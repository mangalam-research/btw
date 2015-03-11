from django_nose import NoseTestSuiteRunner
from django.core.management import call_command
from django.core.management.base import CommandError

class Runner(NoseTestSuiteRunner):

    def setup_test_environment(self):
        super(Runner, self).setup_test_environment()
        call_command('btwredis', 'start')

    def teardown_test_environment(self):
        try:
            super(Runner, self).teardown_test_environment()
        finally:
            call_command('btwredis', 'stop')
