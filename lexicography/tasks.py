from __future__ import absolute_import

import hashlib

from celery.utils.log import get_task_logger
from celery import Task
from django.core.cache import caches
from django.db import router, transaction
from django.conf import settings

from btw.celery import app
from .models import Chunk, ChunkMetadata
from . import depman
from .article import prepare_article_data, get_bibliographical_data
from .caching import make_display_key
from lib.tasks import acquire_mutex, HELD
from lib.existdb import ExistDB, get_path_for_chunk_hash

logger = get_task_logger(__name__)

cache = caches['article_display']

class PreparationTask(Task):  # pylint: disable=abstract-method
    abstract = True

    def on_failure(self, key, exc, task_id, args, kwargs, einfo):
        #
        # The task failed, clean the key.
        #
        cache.delete(key)
        logger.error("%s: has failed with exception: %s", key, einfo)

    def acquire_mutex(self, key):
        if self.request.id is None:
            return True

        return acquire_mutex(cache, key, self.request.id, logger)

class PrepareChunkTask(Task):  # pylint: disable=abstract-method
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        key = make_display_key("xml", args[0])
        logger.error("%s: has failed with exception: %s", key, einfo)

@app.task(base=PrepareChunkTask, acks_late=True)
def prepare_xml(pk):
    """
    This function prepares a chunk for display and caches the
    result of the prepared XML.

    :param pk: The primary key of the chunk to prepare.
    :type pk: :class:`int`
    """

    # By using atomicity and using select_for_update we are
    # effectively preventing other prepare_xml tasks from working on
    # the same chunk at the same time.
    with transaction.atomic():
        chunk = Chunk.objects.get(pk=pk)
        key = chunk.display_key("xml")
        logger.debug("%s processing...", key)
        meta, _ = ChunkMetadata.objects \
            .select_for_update() \
            .get_or_create(chunk=chunk)

        data = chunk.data
        xml, sf_records = prepare_article_data(data)

        cache.set(key, xml, timeout=settings.LEXICOGRAPHY_XML_TIMEOUT)

        logger.debug("%s is set", key)

        sha1 = hashlib.sha1()
        sha1.update(xml.encode('utf-8'))
        xml_hash = sha1.hexdigest()
        db = ExistDB()
        path = get_path_for_chunk_hash("display", pk)
        absent = not db.hasDocument(path)
        if meta.xml_hash != xml_hash or absent:
            # This is something that should not happen ever. It has
            # happened once in development but it is unclear what could
            # have been the cause.
            if meta.xml_hash == xml_hash and absent:
                logger.error("%s was missing from eXist but had a value "
                             "already set and equal to the new hash; this "
                             "should not happen!", path)

            meta.semantic_fields = sf_records
            # Technically, if it was created then xml_hash is already
            # set, but putting this in an conditional block does not
            # provide for better performance.
            meta.xml_hash = xml_hash
            meta.save()
            if not db.load(xml.encode("utf-8"), path):
                raise Exception("could not sync with eXist database")


def fetch_xml(pk):
    """
    This function will check in the cache first and if the xml is not
    present there it will load it from eXist and put it back in the
    cache. This is not actually a task but it is so tightly related to
    the ``process_xml`` task that it is included among the other
    tasks.
    """
    key = make_display_key("xml", pk)
    xml = cache.get(key)
    if xml:
        return xml

    # We make this atomic and use select_for_update so that anything
    # else that might want to mess with our chunks is blocked from
    # doing so until we are done.
    with transaction.atomic():
        try:
            meta = ChunkMetadata.objects \
                                .select_for_update().get(chunk_id=pk)
        except ChunkMetadata.DoesNotExist:
            meta = None

        xml = None
        if meta:
            path = get_path_for_chunk_hash("display", pk)
            db = ExistDB()
            xml = db.getDocument(path).decode("utf-8")

            if xml:
                cache.set(key, xml,
                          timeout=settings.LEXICOGRAPHY_XML_TIMEOUT)

        return xml


class PrepareBiblDataTask(PreparationTask):  # pylint: disable=abstract-method
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        key = make_display_key("bibl", args[0])
        return super(PrepareBiblDataTask, self).on_failure(
            key, exc, task_id, args,
            kwargs, einfo)

@app.task(base=PrepareBiblDataTask, bind=True)
def prepare_bibl(self, pk, test=None):
    # The ``test`` parameter is not documented as it is used only for
    # testing.
    if test is None:
        test = {}

    chunk = Chunk.objects.get(pk=pk)

    key = chunk.display_key("bibl")
    #
    # What we are doing here is try to prevent useless work:
    #
    # 1. It is possible another task has just finished computing the
    # value. We don't want to recompute it for nothing.
    #
    # 2. We do not want to have two tasks compute results from the
    # same change record. The first task that starts should take
    # ownership of the key, so to speak. It does this by setting the
    # key to an object with a "task" field that contains the
    # identifier of the task.
    #
    acquired = self.acquire_mutex(key)
    if not acquired:
        return

    # Simulate a task that mysteriously stops working after it has
    # claimed the key.
    if test.get("vanish"):
        return

    # Simulate a task that fails due to an exception.
    if test.get("fail"):
        raise Exception("failing")

    data = chunk.data
    (targets, bibl_data) = get_bibliographical_data(data)

    for target in targets:
        depman.bibl.record(target, key)

    cache.set(key, bibl_data)

    logger.debug("%s is set", key)
