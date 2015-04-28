from __future__ import absolute_import

import lxml.etree

from celery.utils.log import get_task_logger
from celery import Task
from django.core.cache import caches

from btw.celery import app
from .models import ChangeRecord, Entry
from .xml import XMLTree
from . import depman
from bibliography.views import targets_to_dicts
from lib.tasks import acquire_mutex

logger = get_task_logger(__name__)

cache = caches['article_display']

class PrepareChangerecordTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        #
        # The task failed, clean the key.
        #
        pk = args[0]
        published = kwargs.get('published')

        cr = ChangeRecord.objects.get(pk=pk)
        if published is None:
            published = cr.published

        key = cr.article_display_key(published)
        cache.delete(key)
        logger.error("%s: has failed with exception: %s", key, einfo)

@app.task(base=PrepareChangerecordTask, bind=True)
def prepare_changerecord_for_display(self, pk, published=None,
                                     test=None):
    """
    Modifies the file produced by the authors of the article so that
    it is suitable for display. In particular:

    * Adds the links to other articles present in the database.

    This task will cache the information.

    :param pk: The primary key of the change record to display.
    :type pk: :class:`int`
    :param published: Whether to consider the record as published or
                      not. This overrides the record's actual status.
    :type published: :class:`bool`

    """

    # The ``test`` parameter is not documented as it is used only for
    # testing.
    if test is None:
        test = {}

    cr = ChangeRecord.objects.get(pk=pk)
    if published is None:
        published = cr.published

    key = cr.article_display_key(published)

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

    if not acquire_mutex(cache, key, self.request.id, logger):
        return

    #
    # From this point onwards, we are guaranteed to be the only task
    # computing values for this ChangeRecord.
    #
    logger.debug("%s processing...", key)

    # Simulate a task that mysteriously stops working after it has
    # claimed the key.
    if test.get("vanish"):
        return

    # Simulate a task that fails due to an exception.
    if test.get("fail"):
        raise Exception("failing")

    data = cr.c_hash.data
    xml = XMLTree(data.encode("utf-8"))
    if xml.is_data_unclean():
        raise ValueError("the data is not clean")
    this_lemma = xml.extract_lemma()

    tree = xml.tree
    namespaces = {
        "btw": "http://mangalamresearch.org/ns/btw-storage",
        "tei": "http://www.tei-c.org/ns/1.0"
    }
    terms = tree.xpath(
        "//*[self::btw:antonym or self::btw:cognate "
        "or self::btw:conceptual-proximate]/btw:term | "
        "/btw:entry/btw:overview/btw:definition/tei:p/"
        "tei:foreign[@xml:lang='sa-Latn']",
        namespaces=namespaces)

    candidates = Entry.objects.active_entries()

    if published:
        candidates = candidates.filter(latest_published__isnull=False)

    targets = xml.get_bibilographical_targets()

    lemmas = set()
    for term in terms:
        lemma = u''.join(term.itertext()).strip()
        # Empty lemmas can happen while editing, just skip.
        if not lemma or lemma == this_lemma:
            continue

        lemmas.add(lemma)

    # This creates a map of lemma to Entry in one database query.
    found_lemmas = {
        candidate.lemma: candidate for candidate in
        candidates.filter(lemma__in=lemmas)}

    for term in terms:
        lemma = u''.join(term.itertext()).strip()
        candidate = found_lemmas.get(lemma)

        if candidate is None:
            continue

        ref = lxml.etree.Element("ref")
        ref.set("target", candidate.get_absolute_url())
        ref.text = term.text
        term.text = ''
        ref.extend(term.getchildren())
        ref.tail = term.tail
        term.tail = ''
        term.append(ref)

    bibl_data = targets_to_dicts(targets)

    if not found_lemmas:
        # We do not reserialize an unmodified tree.
        prepared = data
    else:
        prepared = lxml.etree.tostring(tree,
                                       xml_declaration=False,
                                       encoding='utf-8').decode('utf-8')
    #
    # The work we've done becomes obsolete if:
    #
    # 1. A referred article is added or removed (removed ==
    #    unpublished or deleted). We need to add or remove the link.
    #
    # It does not become obsolete if:
    #
    # 1. This ChangeRecord is published or unpublished. The cache key
    #    distinguishes by publication status.
    #
    # 2. A referred article is changed. The URL we generate to link to
    #    the other article will automatically bring the user to the
    #    latest state of the article.
    #
    # 3. The article to which the ChangeRecord belongs changes. The
    #    ChangeRecord's contents is immutable.
    #
    for lemma in lemmas:
        depman.lemma.record(lemma, key)

    for target in targets:
        depman.bibl.record(target, key)

    cache.set(key, {"xml": prepared, "bibl_data": bibl_data})
    logger.debug("%s is set", key)
