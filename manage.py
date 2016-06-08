#!/usr/bin/env python
import os
import sys
import subprocess

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    # We always disable static serving.
    if (len(sys.argv) > 1 and sys.argv[1] == "runserver" and
            (len(sys.argv) < 3 or "--nostatic" not in sys.argv[2:])):
        sys.argv.append("--nostatic")

    testing = len(sys.argv) > 1 and sys.argv[1] == "test"

    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "btw.test_settings" if testing else "btw.settings")

    from lib import env
    env.from_command_line = True
    env.testing = testing or (
        len(sys.argv) > 1 and sys.argv[1] in ("liveserver", "runserver"))

    try:
        # Starting redis cannot be moved to the test runner because it
        # needs to happen before the runner gains control.
        started_redis = False
        if testing:
            # We cannot use call_command here because Django is not
            # yet bootstrapped.
            subprocess.check_call([sys.argv[0], "btwredis", "start",
                                   "--delete-dump"])
            started_redis = True

        execute_from_command_line(sys.argv)
    finally:
        if started_redis:
            try:
                subprocess.check_call([sys.argv[0], "btwredis", "stop",
                                       "--delete-dump"])
            except Exception as ex:  # pylint: disable=broad-except
                print ex
