import re
from copy import deepcopy
from collections import defaultdict

from tatsu.exceptions import FailedParse
import lxml.etree

from .models import Entry
from .xml import XMLTree, default_namespace_mapping, elements_as_text, \
    element_as_text
from bibliography.views import targets_to_dicts
from semantic_fields.models import SemanticField, SearchWord, make_specified_sf
from semantic_fields.util import parse_local_references
from lib.sqlutil import select_for_share

btw_mapping = default_namespace_mapping["btw"]

def prepare_article_data(data):
    """
    Modifies the file produced by the authors of the article so that
    it is suitable for display. In particular:

    * Creates the list of semantic fields that are derived from lists
      of semantic fields that scribes insert in articles.

    * Resolves semantic field numbers to their names and formats the
      names.

    The result is an article which is no longer strictly speaking
    conforming to the btw-storage schema but is what the ``btw_view.js``
    code expects.

    This function must tolerate data that is well-formed but not valid
    according to our storage schema.

    :param data: The XML (in serialization form) of the article.
    """

    tree = XMLTree(data.encode("utf-8"))
    if tree.is_data_unclean():
        raise ValueError("the data is not clean")

    #
    # The series of steps we perform here will turn the article into
    # something which no longer conforms to the btw-storage
    # schema. See the documentation in each function to know what
    # changes are made.
    #

    modified = combine_sense_semantic_fields(tree)
    modified = combine_all_semantic_fields(tree) or modified
    modified = combine_cognate_semantic_fields(tree) or modified
    modified = add_semantic_fields_to_english_renditions(tree) or modified
    modified, sf_records = name_semantic_fields(tree) or modified

    if modified:
        xml = lxml.etree.tostring(tree.tree, encoding="unicode")
    else:
        # We do not reserialize an unmodified tree.
        xml = data

    return xml, sf_records

terms_xpath = lxml.etree.XPath("//*[self::btw:antonym or self::btw:cognate "
                               "or self::btw:conceptual-proximate]/btw:term | "
                               "/btw:entry/btw:overview/btw:definition/tei:p/"
                               "tei:foreign[@xml:lang='sa-Latn']",
                               namespaces=default_namespace_mapping)

def get_lemmas_and_terms(xml):
    this_lemma = xml.extract_lemma()

    # We extract from the tree all the lemmas that appear as part of
    # the article, for instance as an antonym, a cognate, etc. We also
    # include in the list the foreign Sanskrit terms in the
    # definition.
    tree = xml.tree
    terms = terms_xpath(tree)

    # Use a set to eliminate duplicate lemmas.
    lemmas = set()
    for term in terms:
        lemma = ''.join(term.itertext()).strip()
        # Empty lemmas can happen while editing, just skip. We also do
        # not link the article to itself.
        if not lemma or lemma == this_lemma:
            continue

        lemmas.add(lemma)

    return (lemmas, terms)

def hyperlink_prepared_data(prepared, published):
    data = prepared["xml"]
    xml = XMLTree(data.encode("utf-8"))
    (lemmas, terms) = get_lemmas_and_terms(xml)
    modified = hyperlink_article(lemmas, terms, published)
    if modified:
        data = lxml.etree.tostring(xml.tree, encoding="unicode")
    # else we do not reserialize
    return data


def hyperlink_article(lemmas, terms, published):
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
        lemma = ''.join(term.itertext()).strip()
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

    return bool(found_lemmas)


def get_bibliographical_data(data):
    tree = XMLTree(data.encode("utf-8"))
    if tree.is_data_unclean():
        raise ValueError("the data is not clean")
    targets = tree.get_bibilographical_targets()
    bibl_data = targets_to_dicts(targets)

    return (targets, bibl_data)

sfs_in_semantic_fields_xpath = lxml.etree.XPath(
    "//btw:sense/btw:semantic-fields/btw:sf",
    namespaces=default_namespace_mapping)

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
    sfs = sfs_in_semantic_fields_xpath(xml.tree)
    if sfs:
        overview = xml.tree.find("btw:overview",
                                 namespaces=default_namespace_mapping)
        if overview is not None:
            all_sfs = lxml.etree.SubElement(
                overview,
                f"{{{btw_mapping}}}semantic-fields")
            combine_semantic_fields_into(sfs, all_sfs, 3)
            return True

    return False

semantic_fields_outside_cs_xpath = lxml.etree.XPath(
    "(.//btw:citations//btw:sf | .//btw:other-citations//btw:sf)"
    "[not(ancestor::btw:contrastive-section)]",
    namespaces=default_namespace_mapping)

def combine_sense_semantic_fields(xml):
    """
    Combine the semantic fields that appear in the citations of a
    sense, minus those in ``btw:contrastive-section``. These fields
    are combined into a ``btw:semantic-fields`` element that sits
    before the contrastive section of the sense, or at the end of the
    sense if there is no contrastive section.
    """
    senses = xml.tree.findall(".//btw:sense",
                              namespaces=default_namespace_mapping)
    modified = False
    for sense in senses:
        # We are looking only for the first child
        contrastive = sense.find("btw:contrastive-section",
                                 namespaces=default_namespace_mapping)

        # We get all btw:sf elements that are outside the
        # contrastive section.
        sfs = semantic_fields_outside_cs_xpath(sense)
        if sfs:
            modified = True
            sense_sfss = \
                lxml.etree.Element(f"{{{btw_mapping}}}semantic-fields")
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
    cognates = xml.tree.findall(".//btw:cognate",
                                namespaces=default_namespace_mapping)
    modified = False
    for cognate in cognates:
        modified = True
        sfs = cognate.findall(".//btw:sf",
                              namespaces=default_namespace_mapping)

        sfss = lxml.etree.Element(f"{{{btw_mapping}}}semantic-fields")
        combine_semantic_fields_into(sfs, sfss)
        cognate[0].addprevious(sfss)

    return modified


def combine_semantic_fields_into(sfs, into, depth=None):
    texts = elements_as_text(sfs)

    combined = combine_semantic_fields(texts, depth)
    for text in combined:
        sf = lxml.etree.SubElement(into, f"{{{btw_mapping}}}sf")
        sf.text = text


# This is the regular expression we use to remove everything after
# ``|`` or the positional suffix. (We use this *only* for the truncation.)
truncate_re = re.compile(r"\|.*|[a-z]+.*$")

def truncate_to(text, depth):
    parts = truncate_re.sub("", text).split(".", depth)

    # Only perform this transformation if we need to truncate.
    return ".".join(parts[0:depth]) + "n" \
        if len(parts) > depth or (len(parts) == depth and ("|" in text)) \
           else text


key_re = re.compile(r"(?<!\d)(\d{2})(?!\d)")

def key_from_path(x):
    # We add a leading 0 to numbers that do not have it because the
    # HTE project has at least *some* semantic field codes that are
    # 100, 101, etc but they did *not* redesign the codes to be padded
    # with an additional 0. So without the padding we do here, we
    # would sort incorrectly sometimes.
    #
    # The replacement of "." with "~" is done to sort properly. The
    # problem is that "." comes before [a-z] in lexical order. So
    # "01.01.02" would come **before** "01.01aj", even if it is a
    # child of the latter. Mapping "." to "~" takes care of this
    # sorting issue.
    return key_re.sub(r"0\1", x.replace(".", "~"))

def combine_semantic_fields(texts, depth=None):
    return sorted(set(texts if depth is None else (truncate_to(text, depth)
                                                   for text in texts)),
                  key=key_from_path)


def add_semantic_fields_to_english_renditions(xml):
    renditions = xml.tree.findall(".//btw:english-rendition",
                                  namespaces=default_namespace_mapping)
    terms = [element_as_text(x.find("btw:english-term",
                                    namespaces=default_namespace_mapping))
             for x in renditions]
    rendition_to_fields = defaultdict(list)
    for word, path in SearchWord.objects.filter(searchword__in=set(terms))\
            .values_list("searchword", "htid__semantic_field__path"):
        rendition_to_fields[word].append(path)
    # We regenerate the dictionary so that the values are sorted.
    rendition_to_fields = {key: sorted(value, key=key_from_path)
                           for key, value in rendition_to_fields.items()}
    modified = False
    for rendition in renditions:
        term = terms.pop(0)
        try:
            fields = rendition_to_fields[term]
        except KeyError:
            continue
        sfs = lxml.etree.Element(f"{{{btw_mapping}}}semantic-fields")
        for field in fields:
            sf = lxml.etree.SubElement(sfs, f"{{{btw_mapping}}}sf")
            sf.text = field
        rendition.append(sfs)
        modified = True

    return modified

def name_semantic_fields(xml):
    sfs = xml.tree.findall(".//btw:sf",
                           namespaces=default_namespace_mapping)

    #
    # We perform an initial scan so as to avoid hitting the database
    # over and over for the same reference.
    #
    to_fetch = set()
    sf_to_refs = {}
    for sf in set(elements_as_text(sfs)):
        try:
            refs = parse_local_references(sf)
        except (ValueError, FailedParse):
            # We let unparseable cases slide. This allows early display of
            # articles.
            continue

        sf_to_refs[sf] = refs

        for ref in refs:
            while True:
                ref_str = str(ref)

                # Already processed, we don't need to seek this field
                # or its parents.
                if ref_str in to_fetch:
                    break

                to_fetch.add(ref_str)

                # In the cases where a reference has a
                # subcategory, we need to join the subcategory
                # with its parents, up to the first parent which
                # is not a subcategory. So we need to fetch
                # these. Otherwise, we end our processing of this
                # reference.
                if not ref.hte_subcats:
                    break

                # Process the parent.
                ref = ref.parent()

    # We select for update because we do not want the records to change
    # while we are using them.
    sf_records = select_for_share(
        SemanticField.objects.filter(path__in=to_fetch))

    path_to_record = {sf.path: sf for sf in sf_records}

    if not len(path_to_record):
        return False, sf_records

    for sf in sfs:
        text = element_as_text(sf)

        # If text is not in sf_to_refs or str(ref) is not in path_to_record
        # we just continue to the next sf. This allows showing articles
        # that are a work-in-progress.
        try:
            records = [path_to_record[str(ref)] for ref in sf_to_refs[text]]
        except KeyError:
            continue

        records_len = len(records)
        if records_len:
            del sf[:]
            sf.attrib["ref"] = text

            record = records[0] if records_len == 1 else \
                make_specified_sf(records)

            heading = record.heading_for_display

            sf.text = text if heading is None else f"{heading} ({text})"

    return True, sf_records
