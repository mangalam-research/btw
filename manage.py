#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # We always disable static serving.
    if sys.argv[1] == "runserver" and "--nostatic" not in sys.argv[2:]:
        sys.argv.append("--nostatic")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "btw.test_settings" if sys.argv[1] == "test"
                          else "btw.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
