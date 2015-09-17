from __future__ import absolute_import

import re

import lxml.etree

from celery.utils.log import get_task_logger
from celery import Task
from django.core.cache import caches
from grako.exceptions import FailedParse

from btw.celery import app
from .models import ChangeRecord, Entry
from .xml import XMLTree, default_namespace_mapping, elements_as_text, \
    element_as_text
from . import depman
from bibliography.views import targets_to_dicts
from lib.tasks import acquire_mutex
from semantic_fields.models import Category
from semantic_fields.util import parse_local_references

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

    * Creates the list of semantic fields that are derived from lists
      of semantic fields that scribes insert in articles.

    * Resolves semantic field numbers to their names and formats the
      names.

    The result is an article which is no longer strictly speaking
    conforming to the btw-storage schema but is what the ``btw_view.js``
    code expects.

    The task also gathers the bibliographical data necessary for
    displaying the article.

    This task will cache the modified article and the bibliographical
    data.

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

    # Do the actual work...
    modified = False
    (lemmas, modified) = hyperlink_article(data, xml, published)
    (targets, bibl_data) = get_bibliographical_data(xml)
    #
    # The series of steps we perform here will turn the article into
    # something which no longer conforms to the btw-storage
    # schema. See the documentation in each function to know what
    # changes are made.
    #
    modified = combine_sense_semantic_fields(xml) or modified
    modified = combine_all_semantic_fields(xml) or modified
    modified = combine_cognate_semantic_fields(xml) or modified
    modified = name_semantic_fields(xml) or modified

    if not modified:
        # We do not reserialize an unmodified tree.
        prepared = data
    else:
        prepared = lxml.etree.tostring(xml.tree,
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

def hyperlink_article(data, xml, published):
    this_lemma = xml.extract_lemma()

    # We extract from the tree all the lemmas that appear as part of
    # the article, for instance as an antonym, a cognate, etc. We also
    # include in the list the foreign Sanskrit terms in the
    # definition.
    tree = xml.tree
    terms = tree.xpath(
        "//*[self::btw:antonym or self::btw:cognate "
        "or self::btw:conceptual-proximate]/btw:term | "
        "/btw:entry/btw:overview/btw:definition/tei:p/"
        "tei:foreign[@xml:lang='sa-Latn']",
        namespaces=default_namespace_mapping)

    # Use a set to eliminate duplicate lemmas.
    lemmas = set()
    for term in terms:
        lemma = u''.join(term.itertext()).strip()
        # Empty lemmas can happen while editing, just skip. We also do
        # not link the article to itself.
        if not lemma or lemma == this_lemma:
            continue

        lemmas.add(lemma)

    # The candidates are those articles that *could* be the target of
    # a link.
    candidates = Entry.objects.active_entries()

    # If this article is published, we link only to published articles.
    if published:
        candidates = candidates.filter(latest_published__isnull=False)

    # This creates a map of lemma to Entry in one database query. The
    # map contains only those lemmas for which we *can* hyperlink.
    found_lemmas = {
        candidate.lemma: candidate for candidate in
        candidates.filter(lemma__in=lemmas)}

    for term in terms:
        lemma = u''.join(term.itertext()).strip()
        candidate = found_lemmas.get(lemma)

        # We just leave intact those terms we cannot link.
        if candidate is None:
            continue

        # Otherwise, modify the term so that it holds a reference to
        # the other article.
        ref = lxml.etree.Element("ref")
        ref.set("target", candidate.get_absolute_url())
        ref.text = term.text
        term.text = ''
        ref.extend(term.getchildren())
        ref.tail = term.tail
        term.tail = ''
        term.append(ref)

    return (lemmas, bool(found_lemmas))


def get_bibliographical_data(xml):
    targets = xml.get_bibilographical_targets()
    bibl_data = targets_to_dicts(targets)

    return (targets, bibl_data)

def combine_all_semantic_fields(xml):
    """
    Create the "all semantic fields" section from the semantic fields
    of each sense. This must be performed after we've created the list
    of semantic fields for each sense. This function grabs the list of
    semantic fields we previous created for senses (i.e. the semantic
    fields in the ``btw:semantic-fields`` element which is the
    immediate child of ``btw:sense``) and appends a new
    ``btw:semantic-fields`` element to ``btw:overview``.

    Semantic fields thus combined are truncated to 3 levels, and
    duplicates are eliminated.
    """
    all_sfs = lxml.etree.Element(
        "{{{0}}}semantic-fields".format(default_namespace_mapping["btw"]),
        nsmap=default_namespace_mapping)
    sfs = xml.tree.xpath("//btw:sense/btw:semantic-fields/btw:sf",
                         namespaces=default_namespace_mapping)
    if sfs:
        combine_semantic_fields_into(sfs, all_sfs, 3)
        overview = xml.tree.xpath("//btw:overview",
                                  namespaces=default_namespace_mapping)[0]
        overview.append(all_sfs)
        return True

    return False

def combine_sense_semantic_fields(xml):
    """
    Combine the semantic fields that appear in the citations of a
    sense, minus those in ``btw:contrastive-section``. These fields
    are combined into a ``btw:semantic-fields`` element that sits
    before the contrastive section of the sense, or at the end of the
    sense if there is no contrastive section.
    """
    senses = xml.tree.xpath(
        "//btw:sense", namespaces=default_namespace_mapping)
    modified = False
    for sense in senses:
        contrastives = sense.xpath(
            ".//btw:contrastive-section", namespaces=default_namespace_mapping)
        contrastive = contrastives[0] if contrastives else None

        # We get all btw:sf elements that are outside the
        # contrastive section.
        sfs = sense.xpath("(.//btw:citations//btw:sf | "
                          ".//btw:other-citations//btw:sf)"
                          "[not(ancestor::btw:contrastive-section)]",
                          namespaces=default_namespace_mapping)
        if sfs:
            modified = True
            sense_sfss = lxml.etree.Element(
                "{{{0}}}semantic-fields".format(
                    default_namespace_mapping["btw"]),
                nsmap=default_namespace_mapping)
            combine_semantic_fields_into(sfs, sense_sfss)
            if contrastive is not None:
                contrastive.addprevious(sense_sfss)
            else:
                sense.append(sense_sfss)

    return modified


def combine_cognate_semantic_fields(xml):
    """
    For each ``btw:cognate``, this function adds a
    ``btw:semantic-fields`` element that is a combination of all the
    semantic fields in the cognate. The new element is added at the
    very start of the ``btw:cognate`` element.
    """
    cognates = xml.tree.xpath(
        "//btw:cognate", namespaces=default_namespace_mapping)
    modified = False
    for cognate in cognates:
        modified = True
        sfs = cognate.xpath(".//btw:sf",
                            namespaces=default_namespace_mapping)

        sfss = lxml.etree.Element(
            "{{{0}}}semantic-fields".format(default_namespace_mapping["btw"]),
            nsmap=default_namespace_mapping)
        combine_semantic_fields_into(sfs, sfss)
        cognate[0].addprevious(sfss)

    return modified


def combine_semantic_fields_into(sfs, into, depth=None):
    texts = elements_as_text(sfs)

    combined = combine_semantic_fields(texts, depth)
    for text in combined:
        sf = lxml.etree.Element("{{{0}}}sf".format(
            default_namespace_mapping["btw"]), nsmap=default_namespace_mapping)
        sf.text = text
        into.append(sf)


# This is the regular expression we use to remove everything after
# ``|`` or the positional suffix. (We use this *only* for the truncation.)
truncate_re = re.compile(r"\|.*|[a-z]+.*$")

def truncate_to(text, depth):
    parts = truncate_re.sub("", text).split(".")

    # Only perform this transformation if we need to truncate.
    if len(parts) > depth or (len(parts) == depth and ("|" in text)):
        # We always add "n" as the pos when we truncate.
        return ".".join(truncate_re.sub("", text).split(".")[0:depth]) + "n"

    return text


key_re = re.compile(r"(?<!\d)(\d{2})(?!\d)")

def combine_semantic_fields(texts, depth=None):
    return sorted(set(texts if depth is None else (truncate_to(text, depth)
                                                   for text in texts)),
                  # We add a leading 0 to numbers that do not have it
                  # because the HTE project has at least *some*
                  # semantic field codes that are 100, 101, etc but
                  # they did *not* redesign the codes to be padded
                  # with an additional 0. So without the padding we do
                  # here, we would sort incorrectly sometimes.
                  #
                  # The replacement of "." with "~" is done to sort
                  # properly. The problem is that "." comes before
                  # [a-z] in lexical order. So "01.01.02" would come
                  # **before** "01.01aj", even if it is a child of the
                  # latter. Mapping "." to "~" takes care of this
                  # sorting issue.
                  key=lambda x: key_re.sub(r"0\1", x.replace(".", "~")))


def name_semantic_fields(xml):
    sfs = xml.tree.xpath("//btw:sf", namespaces=default_namespace_mapping)

    #
    # We perform an initial scan so as to avoid hitting the database
    # over and over for the same reference.
    #

    # This is a set of references we've tried to resolve, whether
    # successfully or not. We use this to prevent hitting the database
    # multiple times rather than ``used`` so that ``used`` contains only
    # references that resolve to **something**.
    fetched = set()
    # This is a map from reference its resolution from the database.
    used = {}
    for sf in set(elements_as_text(sfs)):
        category = None

        try:
            refs = parse_local_references(sf)
        except (ValueError, FailedParse):
            # We let unparseable cases slide. This allows early display of
            # articles.
            continue

        for ref in refs:
            ref_str = unicode(ref)
            if ref_str not in fetched:
                try:
                    category = Category.objects.get(path=ref_str)
                except Category.DoesNotExist:
                    continue

                fetched.add(ref_str)

                if category is not None:
                    used[ref_str] = category

    if not used:
        return False

    for sf in sfs:
        text = element_as_text(sf)
        try:
            refs = parse_local_references(text)
        except (ValueError, FailedParse):
            # We let unparseable cases slide. This allows early display of
            # articles.
            continue

        ref_categories = [(ref, used.get(ref, None)) for ref in
                          (unicode(ref) for ref in refs)]

        sep = ''
        if ref_categories:
            del sf[:]
            sf.text = ''
            if len(ref_categories) > 1:
                sep = " @"

        for (ref, category) in ref_categories:
            if category is not None:
                sf.text = category.heading + " (" + ref + ")"
            else:
                sf.text = ref

            sf.text += sep

    return bool(used)
