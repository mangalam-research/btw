from io import StringIO

# We need to use this class rather than call_command if we want to be
# able to capture some diagnostic information when an exception is
# raised. If we do:
#
# stdout, stderr = call_command(...)
#
# And an exception is raised, then the assignment is not done and
# there is nothing to examine. Conversely, this works:
#
# c = Caller()
# try:
#     c.call_command(...)
# finally:
#     self.assertEqual(c.stdout, "bar")
#
#
class Caller(object):

    def __init__(self):
        self._stdout = None
        self._stderr = None
        self.called = False

    def call_command(self, *args, **kwargs):
        self.called = True
        from django.core.management import call_command as cc
        self._stdout = stdout = StringIO()
        self._stderr = stderr = StringIO()
        kwargs["stdout"] = stdout
        kwargs["stderr"] = stderr
        return cc(*args, **kwargs)

    @property
    def stdout(self):
        return self._stdout.getvalue()

    @property
    def stderr(self):
        return self._stderr.getvalue()

def call_command(*args, **kwargs):
    from django.core.management import call_command as cc
    stdout = StringIO()
    stderr = StringIO()
    kwargs["stdout"] = stdout
    kwargs["stderr"] = stderr
    cc(*args, **kwargs)
    return stdout.getvalue(), stderr.getvalue()
