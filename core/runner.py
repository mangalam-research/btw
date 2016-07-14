import sys
import subprocess

from django.core.management import call_command
from django_nose import NoseTestSuiteRunner

from lib.testutil import unmonkeypatch_databases

class Runner(NoseTestSuiteRunner):

    created_exist_db = False
    loaded_index = False

    def setup_databases(self, *args, **kwargs):
        unmonkeypatch_databases()
        ret = super(Runner, self).setup_databases(*args, **kwargs)
        # Createdb will fail if the database already exists. So we run
        # a dropdb first in case the previous run was dirty.
        call_command("btwexistdb", "dropdb")
        call_command("btwexistdb", "createdb")
        self.created_exist_db = True
        call_command("btwexistdb", "loadindex")
        self.loaded_index = True
        return ret

    def teardown_databases(self, *args, **kwargs):
        ret = super(Runner, self).teardown_databases(*args, **kwargs)

        if self.created_exist_db:
            try:
                call_command("btwexistdb", "dropdb")
            except Exception as ex:  # pylint: disable=broad-except
                print ex

        if self.loaded_index:
            try:
                call_command("btwexistdb", "dropindex")
            except Exception as ex:  # pylint: disable=broad-except
                print ex

        return ret
