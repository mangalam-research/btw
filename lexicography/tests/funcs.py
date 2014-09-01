"""
Functions that cannot be put into the ``util`` module. The
``util`` module imports parts of the lexicography app that require a
running Django environment. So it cannot be loaded outside of
Django. Some funciton useful for testing, however, need to be used
outside a Django environment (e.g. on the client side of a Selenium
test). This is why this module exists.
"""
import json
from StringIO import StringIO

import lxml.etree


def parse_search_results(data):
    """
    Parses the results obtained from the
    :class:`lexicography.SearchTable` view. This is a view that
    returns data in JSON format for a DataTable object on the client
    side.

    :param data: The whole JSON data.
    :type data: :class:`str`.
    """
    payload = json.loads(data)
    rows = payload["aaData"]
    parser = lxml.etree.HTMLParser()

    ret = {}
    for row in rows:
        assert len(row) == 1, "unexpected row length"
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
            raise ValueError("unexpected number of links: " + len(els))

        headword = view_link.text
        hit = {
            "headword": headword,
            # Must test with "is not None" to satisfy lxml.
            "edit_url": edit_link.get("href") if edit_link is not None
            else None,
            "view_url": view_link.get("href")
        }
        assert headword not in ret, "headword already defined: " + headword
        ret[headword] = hit

    return ret
