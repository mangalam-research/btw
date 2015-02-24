import datetime
import mock


from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import get_cache

from .util import TestMeta, replay, record
from .. import tasks
from ..models import Item
from lib.util import WithStringIO, utcnow

cache = get_cache('bibliography')

@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory')
class TasksTestCase(TestCase):
    __metaclass__ = TestMeta

    def setUp(self):
        cache.clear()
        super(TasksTestCase, self).setUp()

    @replay
    def test_fetch_items(self):
        """
        Tests that the task populates the Item table and that FETCH_KEY
        and FETCH_KEY are set appropriately.
        """
        self.assertIsNone(cache.get(tasks.FETCH_KEY))
        self.assertIsNone(cache.get(tasks.FETCH_DATE_KEY))
        items = Item.objects.all()
        self.assertEqual(items.count(), 0)

        tasks.fetch_items.delay().get()
        self.assertIsNone(cache.get(tasks.FETCH_KEY))
        last_fetch = cache.get(tasks.FETCH_DATE_KEY)
        self.assertTrue(utcnow() - last_fetch < datetime.timedelta(seconds=5))

        items = Item.objects.all()
        self.assertEqual(items.count(), 47)

    @replay
    def test_fetch_items_loads_new_items(self):
        """
        Tests that the task loads new items.
        """
        items = Item.objects.all()
        self.assertEqual(items.count(), 0)

        tasks.fetch_items.delay().get()

        nr = 47
        items = Item.objects.all()
        self.assertEqual(items.count(), nr)

        # We simulate the addition of a new item by deleting an item
        # already in the database.

        item = Item.objects.all()[0]
        item.delete()

        items = Item.objects.all()
        self.assertEqual(items.count(), nr - 1)

        tasks.fetch_items.delay().get()

        items = Item.objects.all()
        self.assertEqual(items.count(), nr)

        # This would raise an exception if the item does not exist
        self.assertEqual(Item.objects.filter(item_key=item.item_key).count(),
                         1)

    @replay
    def test_fetch_items_loads_changes(self):
        """
        Tests that the task loads new items.
        """
        items = Item.objects.all()
        self.assertEqual(items.count(), 0)

        tasks.fetch_items.delay().get()

        nr = 47
        items = Item.objects.all()
        self.assertEqual(items.count(), nr)

        # We simulate the a change by modifying an item already in the
        # database.

        item = Item.objects.all()[0]
        orig_title = item.title
        item.title += " changed"
        item.save()

        tasks.fetch_items.delay().get()

        items = Item.objects.all()
        self.assertEqual(items.count(), nr)

        # This would raise an exception if the item does not exist
        reloaded = Item.objects.get(item_key=item.item_key)
        self.assertTrue(reloaded.title, orig_title)

    def test_fetch_items_vanish(self):
        """
        Tests that if a task is already in progress, new tasks stop
        running early.
        """
        tasks.fetch_items.delay(test={"vanish": True}).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            tasks.fetch_items.delay().get()
            self.assertLogRegexp(
                handler,
                stream,
                "^fetch is held by (?:.*?); ending task.$")

    def test_prepare_changerecord_for_display_fail(self):
        """
        Tests that a catastrophic failure does not leave a
        record in the cache.
        """
        try:
            tasks.fetch_items.delay(test={"fail": True}).get()
        except Exception as ex:  # pylint: disable=broad-except
            self.assertEqual(str(ex), "failing")

        self.assertIsNone(
            cache.get(tasks.FETCH_KEY),
            "there should not be any information recorded in "
            "the cache for this change record")

    def assertLogRegexp(self, handler, stream, regexp):
        handler.flush()
        self.assertRegexpMatches(stream.getvalue(), regexp)

    @replay
    def test_periodic_fetch_items_is_periodic(self):
        """
        Tests that periodic fetch items really executes periodically.
        """
        tasks.FETCH_ITEM_PERIOD = 1

        state = {
            "remaining": 2
        }
        old_async = tasks.PeriodicFetchItemsTask.apply_async

        def apply_async_mock(self, *args, **kwargs):
            if state["remaining"] > 0:
                state["remaining"] -= 1
                return old_async(self, *args, **kwargs)

        with mock.patch.multiple(tasks.__name__ + ".PeriodicFetchItemsTask",
                                 apply_async=apply_async_mock):
            with WithStringIO(tasks.logger) as (stream, handler):
                tasks.periodic_fetch_items.delay().get()
                self.assertLogRegexp(
                    handler,
                    stream,
                    "^(fetching all bibliographical items\n){2}$")
