from django.dispatch import receiver
from django.core.cache import get_cache

from . import signals
from . import depman
from bibliography import signals as bibsignals

cache = get_cache('article_display')

@receiver(signals.entry_available)
@receiver(signals.entry_unavailable)
@receiver(signals.entry_newly_published)
@receiver(signals.entry_unpublished)
def invalidate_entry_dependents(sender, **kwargs):
    #
    # We've kept the logic simple. It *could* be optimized by looking
    # at the publication status of the change records that depend on
    # the lemma that is changing, and only invalidating the cached
    # information of those records that would be affected. However,
    # this would complicate the logic and multiply the testing paths
    # quite a bit. We leave this as a possible future
    # optimization. (There's also a non-negligible possibility that
    # adding features to BTW may make the optimization moot before we
    # get around to implementing it, so...). The keys we record in the
    # cache already contain all the information that would be needed
    # for the more refined version of the algorithm.
    #

    lemma = kwargs['instance'].lemma

    deps = depman.lemma.get(lemma)

    if not deps:
        return

    depman.lemma.delete(lemma)

    #
    # Delete the article information. It is important that this be
    # done **last**, because this helps avoid race conditions with
    # tasks.prepare_changerecord_for_display.
    #
    cache.delete_many(deps)

@receiver(bibsignals.item_updated)
@receiver(bibsignals.primary_source_updated)
def invalidate_bibl_dependents(sender, **kwargs):
    signal = kwargs['signal']
    instances = [kwargs['instance']] if signal is bibsignals.item_updated \
        else kwargs['instances']

    all_urls = [instance.url for instance in instances]

    deps = depman.bibl.get_union(all_urls)
    depman.bibl.delete_many(all_urls)

    #
    # Delete the article information. It is important that this be
    # done **last**, because this helps avoid race conditions with
    # tasks.prepare_changerecord_for_display.
    #
    if deps:
        cache.delete_many(deps)
