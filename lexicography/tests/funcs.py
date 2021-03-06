"""
Functions that cannot be put into the ``util`` module. The
``util`` module imports parts of the lexicography app that require a
running Django environment. So it cannot be loaded outside of
Django. Some funciton useful for testing, however, need to be used
outside a Django environment (e.g. on the client side of a Selenium
test). This is why this module exists.
"""
import json
from io import StringIO

import lxml.etree


def parse_search_results(data):  # pylint: disable=too-many-locals
    """
    Parses the results obtained from the
    :class:`lexicography.SearchTable` view. This is a view that
    returns data in JSON format for a DataTable object on the client
    side.

    :param data: The whole JSON data.
    :type data: :class:`str`.
    :returns: A :class:`dict` that has for keys the lemmata and for
              values a :class:`dict` with the keys: ``"lemma"``
              which has for value the lemma, ``"edit_url"`` which
              has for value the edit URL related to this lemma
              (there can be only one per lemma), ``"hits"`` which
              is a list of each individual hits encountered. Each item
              in the ``"hits"`` list is a dictionary with two keys:
              ``"edit_url"`` is the edit URL that was found in this
              hit and ``"view_url"`` is the URL for viewing the entry
              that was found in this hit. Note: the ``len(..)`` of the
              return value gives the number of different lemmata
              that were found. The total number of rows found in the
              table is obtained by adding the ``len(..)`` of each
              ``hits`` list.
    """
    payload = json.loads(data)
    rows = payload["data"]
    parser = lxml.etree.HTMLParser()

    ret = {}
    for row in rows:
        assert len(row) == 7, "unexpected row length"
        cell = row[0]
        tree = lxml.etree.parse(StringIO(cell), parser)
        els = tree.xpath("//a")
        edit_link = None
        if len(els) == 1:
            view_link = els[0]
        elif len(els) == 2:
            view_link = els[1]
            edit_link = els[0]
        else:
            raise ValueError("unexpected number of links in first cell: " +
                             str(len(els)))

        cell = row[1]
        tree = lxml.etree.parse(StringIO(cell), parser)
        schema_version = cell.split("<", 1)[0].strip()
        schema_update = len(tree.xpath("//span")) != 0

        cell = row[2]
        tree = lxml.etree.parse(StringIO(cell), parser)
        els = tree.xpath("//a")
        publish_link = els[0] if len(els) == 1 else None
        published = None

        if cell == "Yes" or cell.startswith("Yes "):
            published = True
        elif cell == "No" or cell.startswith("No "):
            published = False
        else:
            raise ValueError("publication status cell "
                             "contains unexpected text: " + cell)

        lemma = view_link.text
        hit = {
            # Must test with "is not None" to satisfy lxml.
            "edit_url": (edit_link.get("href") if edit_link is not None
                         else None),
            "view_url": view_link.get("href"),
            "publish_url":
            publish_link.get("href") if publish_link is not None else None,
            "deleted": row[3],
            "datetime": row[4],
            "published": published,
            "schema_version": schema_version,
            "schema_update": schema_update
        }
        lemma_rec = ret.get(lemma)
        if lemma_rec:
            if hit["edit_url"]:
                assert lemma_rec["edit_url"] is None, \
                    "can't have two edit urls"
                lemma_rec["edit_url"] = hit["edit_url"]
        else:
            lemma_rec = {
                "lemma": lemma,
                "edit_url": hit["edit_url"],
                "hits": []
            }
            ret[lemma] = lemma_rec

        lemma_rec["hits"].append(hit)

    return ret


def count_hits(hits):
    return sum(len(hit["hits"]) for hit in hits.values())
