from django.dispatch import receiver
from django.core.cache import caches

from . import depman
from . import signals
from bibliography import signals as bibsignals
from semantic_fields import signals as semsignals

cache = caches['article_display']

@receiver(semsignals.semantic_field_updated)
def invalidate_semantic_field_dependents(sender, **kwargs):
    from .tasks import prepare_xml
    instance = kwargs['instance']
    keys = set()
    pks = set()
    for chunk in instance.chunkmetadata_set.all():
        keys.add(chunk.display_key("xml"))
        pks.add(chunk.pk)

    cache.delete_many(keys)
    for pk in pks:
        prepare_xml.delay(pk)

@receiver(bibsignals.item_updated)
@receiver(bibsignals.primary_source_updated)
def invalidate_bibl_dependents(sender, **kwargs):
    signal = kwargs['signal']
    instances = [kwargs['instance']] if signal is bibsignals.item_updated \
        else kwargs['instances']

    all_urls = [instance.abstract_url for instance in instances]

    # Find all articles that need recomputing.
    deps = depman.bibl.get_union(all_urls)

    # We invalidate the dependency information of all the instances
    # that have changed.
    depman.bibl.delete_many(all_urls)

    #
    # Delete the article information. It is important that this be
    # done **last**, because this helps avoid race conditions with
    # tasks.prepare_chunk.
    #
    if deps:
        cache.delete_many(deps)

def make_display_key(kind, pk):
    if kind not in ("bibl", "xml"):
        raise ValueError("unknown display key kind {}".format(kind))
    return "{}_{}".format(pk, kind).encode("ascii")

@receiver(signals.changerecord_hidden)
@receiver(signals.changerecord_shown)
def recheck_chunk(sender, **kwargs):
    instance = kwargs['instance']

    instance.c_hash.visibility_update()
