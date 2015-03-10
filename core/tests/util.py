from cStringIO import StringIO

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
