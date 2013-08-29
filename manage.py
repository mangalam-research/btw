#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    # We always disable static serving.
    if "runserver" in sys.argv and "--nostatic" not in sys.argv:
        sys.argv.append("--nostatic")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "btw.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
