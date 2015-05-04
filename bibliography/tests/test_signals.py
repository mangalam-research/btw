"""
Even though signals are generated by the models, they are a
concern that crosses across the kind of testing we do on models, so we
have a separate module for testing them.

"""

from django.test import TestCase
import mock

from .. import signals, tasks
from ..models import Item, PrimarySource
from . import mock_zotero

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


mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Name 1 for Title 1"},
                {"firstName": "FirstName 2 for Title 1",
                 "lastName": "LastName 2 for Title 1"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "2",
            "title": "Title 2",
            "date": "Date 2",
            "creators": [
                {"name": "Name 1 for Title 2"},
                {"firstName": "FirstName 2 for Title 2",
                 "lastName": "LastName 2 for Title 2"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    }
])

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

class TestMeta(type):

    def __new__(meta, name, bases, dct):
        expand = dct.get("expand")
        for method, fields in expand.iteritems():
            callee = dct[method]

            for field in fields:
                def maketest(c, f):
                    def test(self):
                        c(self, f)
                    return test
                name = "test_{0}_change_{1}".format(field, method)
                test = maketest(callee, field)
                test.__name__ = name
                test.__doc__ = callee.__doc__.format(field)
                dct[name] = test

        return super(TestMeta, meta).__new__(meta, name, bases, dct)


class SignalTestCase(TestCase):
    __metaclass__ = TestMeta

    expand = {
        "check_item_change": ("title", "creators", "date")
    }

    def setUp(self):
        mock_records.reset()
        self.signals = (signals.item_updated,
                        signals.primary_source_updated)
        super(SignalTestCase, self).setUp()
        self.patch = mock.patch.multiple("bibliography.zotero.Zotero",
                                         get_all=get_all_mock,
                                         get_item=get_item_mock)
        self.patch.start()
        tasks.fetch_items()

    def tearDown(self):
        self.patch.stop()
        super(SignalTestCase, self).tearDown()

    def alter_item(self, record, field):
        data = record["data"]

        if field in ("title", "date"):
            data[field] += " (bis)"
        elif field == "creators":
            data["creators"][0]["name"] += " (bis)"
        else:
            raise ValueError("unknown field")

    def assertSignals(self, grabber, expected):
        ex = {signal: [] for signal in self.signals}
        ex.update(expected)
        self.assertEqual(grabber.received, ex)

    def test_item_creation_does_not_generate_item_updated(self):
        with SignalGrabber(self.signals) as grabber:

            item = Item(item_key="9999", uid=Item.objects.zotero.full_uid)
            item.save()
            self.assertSignals(grabber, {})

    def check_item_change(self, field):
        """
        Tests changing an item's {0} field generates an item_updated signal and
        a primary_source_updated signal.
        """
        item = Item.objects.get(item_key="1")

        pss = []
        for title in ("ps1", "ps2"):
            ps = PrimarySource(item=item, reference_title=title,
                               genre="SU")
            ps.save()
            pss.append(ps)

        with SignalGrabber(self.signals) as grabber:
            self.alter_item(mock_records.values[0], field)
            tasks.fetch_items()
            Item.objects.get(pk=item.pk)
            self.assertSignals(grabber, {
                signals.item_updated: [{'instance': item}],
                signals.primary_source_updated: [{'instances': pss}]
            })

    def test_primarysource_creation_does_not_generate_primary_source_updated(
            self):
        item = Item.objects.get(item_key="1")
        with SignalGrabber(self.signals) as grabber:
            ps = PrimarySource(item=item, reference_title="Foo",
                               genre="SU")
            ps.save()
            self.assertSignals(grabber, {})

    def test_primarysource_title_change_generates_primary_source_updated(self):
        item = Item.objects.get(item_key="1")
        ps = PrimarySource(item=item, reference_title="Foo",
                           genre="SU")
        ps.save()
        with SignalGrabber(self.signals) as grabber:
            ps.reference_title = "blah"
            ps.save()
            self.assertSignals(grabber, {
                signals.primary_source_updated: [{'instances': [ps]}]
            })

    def test_ps_genre_change_does_not_generate_primary_source_updated(self):
        item = Item.objects.get(item_key="1")
        ps = PrimarySource(item=item, reference_title="Foo",
                           genre="SU")
        ps.save()
        with SignalGrabber(self.signals) as grabber:
            ps.genre = "SH"
            ps.save()
            self.assertSignals(grabber, {})
