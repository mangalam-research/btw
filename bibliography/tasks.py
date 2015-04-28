from __future__ import absolute_import

from celery.utils.log import get_task_logger
from celery import Task
from django.core.cache import caches

from btw.celery import app
from .zotero import Zotero, zotero_settings
from .models import Item
from lib.tasks import acquire_mutex
from lib.util import utcnow

logger = get_task_logger(__name__)
btw_zotero = Zotero(zotero_settings(), 'BTW Library')

cache = caches['bibliography']

# These are keys we use in the bibliography cache. They cannot clash
# with the keys set from fetching items from the Zotero database as
# keys produced while fetching items are base64-encoded URLs.
FETCH_KEY = "fetch"
FETCH_DATE_KEY = "fetch.date"

def fetch_the_items(task, test=None):
    """
    Fetch the bibliographical items from the Zotero database.
    """

    if test is None:
        test = {}

    # There's another task running.
    if not acquire_mutex(cache, FETCH_KEY, task.request.id, logger):
        return

    # Simulate a task that mysteriously stops working after it has
    # claimed the key.
    if test.get("vanish"):
        return

    # Simulate a task that fails due to an exception.
    if test.get("fail"):
        raise Exception("failing")

    logger.info("fetching all bibliographical items")
    search_results = btw_zotero.get_all()
    for result in search_results:
        key = result["data"]["key"]
        try:
            item = Item.objects.get(item_key=key)
            item.refresh(result)
        except Item.DoesNotExist:
            item = Item(item_key=key, uid=btw_zotero.full_uid)
            item.refresh(result)

    # We're done
    cache.set(FETCH_DATE_KEY, utcnow())
    cache.delete(FETCH_KEY)

class FetchItemsTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        #
        # The task failed, clean the key.
        #
        cache.delete(FETCH_KEY)
        logger.error("failed with exception %s", einfo)

@app.task(base=FetchItemsTask, bind=True, ignore_results=True)
def fetch_items(self, test=None):
    fetch_the_items(self, test)

# We don't get it from settings as this is not meant to be customized.
FETCH_ITEM_PERIOD = 25 * 60

# Inherit from FetchItemsTask so that we get that behavior on
# failures, etc.
class PeriodicFetchItemsTask(FetchItemsTask):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super(PeriodicFetchItemsTask, self).on_failure(
            exc, task_id, args, kwargs, einfo)
        logger.error("has failed with exception: %s", einfo)
        self._reschedule()

    def on_success(self, retval, task_id, args, kwargs):
        super(PeriodicFetchItemsTask, self).on_success(
            retval, task_id, args, kwargs)
        self._reschedule()

    def _reschedule(self):
        self.apply_async((), countdown=FETCH_ITEM_PERIOD)


@app.task(base=PeriodicFetchItemsTask, bind=True, ignore_results=True)
def periodic_fetch_items(self):
    fetch_the_items(self)
