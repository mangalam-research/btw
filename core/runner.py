from django_nose import NoseTestSuiteRunner

from lib.testutil import unmonkeypatch_databases

class Runner(NoseTestSuiteRunner):

    def setup_databases(self, *args, **kwargs):
        unmonkeypatch_databases()
        ret = super(Runner, self).setup_databases(*args, **kwargs)
        return ret
