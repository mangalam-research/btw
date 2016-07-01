from nose.plugins.attrib import attr
from unittest import TestCase

__all__ = ['unmonkeypatch_databases', 'SignalGrabber', 'wipd']

def unmonkeypatch_databases():
    # Undo the monkeypatching we did in __init__ to detect
    # database accesses happening before we actually set our
    # environment to run the tests.
    from django.db import connections
    for name in connections:
        conn = connections[name]
        conn.connect = conn._old_connect

class SignalGrabber(object):

    def __init__(self, signals):
        self.received = None
        self.signals = signals

    def __enter__(self):
        self.received = {signal: [] for signal in self.signals}
        for signal in self.signals:
            signal.connect(self.handler)
        return self

    def handler(self, sender, **kwargs):
        # Yes, we remove the "signal" key from kwargs.
        signal = kwargs.pop("signal")
        self.received[signal].append(kwargs)

    def __exit__(self, exc_type, exc_value, traceback):
        for signal in self.signals:
            signal.disconnect(self.handler)

def wipd(f):
    return attr('wip')(f)
