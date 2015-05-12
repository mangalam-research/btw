#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # We always disable static serving.
    if (len(sys.argv) > 1 and sys.argv[1] == "runserver"
            and (len(sys.argv) < 3 or "--nostatic" not in sys.argv[2:])):
        sys.argv.append("--nostatic")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "btw.test_settings" if len(sys.argv) > 1 and
                          sys.argv[1] == "test"
                          else "btw.settings")

    if len(sys.argv) > 1 and sys.argv[1] == "btwredis":
        from django.conf import settings
        settings.INSTALLED_APPS = ['btw_management']

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
