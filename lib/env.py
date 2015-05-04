from_command_line = False
"""
This is a flag indicating whether we are running from the command
line or not. This should be set only by the ``manage.py`` script. It
can be read by all.
"""

testing = False
"""
This is a flag to be used with ``from_command_line``. This flag
will be true if the command that we are running is a "testing"
command.

Note that the ``BTW_TESTING`` setting is not a substitute for this
flag. When we run a test and the test starts children ``./manage.py``
processes, the ``DJANGO_SETTINGS_MODULE`` which is set in the parent
process will ensure that children all get the same settings. So
``BTW_TESTING`` will be true for the parent and all its children.

When running a test command that starts children, the ``testing`` flag
will be true **only** in the parent ``./manage.py test``
command. Children started from it will see this flag as false.
"""
