
from django.test import TestCase

from ..models import SemanticField
from ..signals import semantic_field_updated
from lib.testutil import SignalGrabber

class SemanticFieldTestCase(TestCase):

    signals = (semantic_field_updated, )

    def assertSignals(self, grabber, expected):
        ex = {signal: [] for signal in self.signals}
        ex.update(expected)
        self.assertEqual(grabber.received, ex)

    def test_heading_change_emits_signal(self):
        """
        Test that changing a heading emits a signal.
        """
        with SignalGrabber(self.signals) as grabber:
            sf = SemanticField(path="01.01n")
            sf.save()
            sf.heading = "Q"
            sf.save()
            self.assertSignals(grabber, {
                semantic_field_updated: [{'instance': sf}]
            })

    def test_resave_does_not_emit_signal(self):
        """
        Test that resaving does not emit a signal.
        """
        with SignalGrabber(self.signals) as grabber:
            sf = SemanticField(path="01.01n")
            sf.save()
            sf.save()
            self.assertSignals(grabber, {})

    def test_change_non_heading_does_not_emit_signal(self):
        """
        Test that changing something else than the heading does not emit.
        """
        with SignalGrabber(self.signals) as grabber:
            sf = SemanticField(path="01.01n")
            sf.save()
            sf.path = "01.02n"
            sf.save()
            self.assertSignals(grabber, {})
