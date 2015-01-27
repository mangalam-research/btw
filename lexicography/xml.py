"""XML parsing and conversion utilities.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import lxml.etree

import os
import re

import lib.util as util

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")
xsl_dirname = os.path.join(dirname, "../utils/xsl/")


def schema_for_version(version):
    path = schema_for_version_unsafe(version)
    if path is None:
        raise ValueError("unknown version: " + version)

    return path

def schema_for_version_unsafe(version):
    path = os.path.join(schemas_dirname,
                        "out/btw-storage-%s/btw-storage.rng" % version)

    if not os.path.exists(path):
        return None

    return path


_NO_SCHEMATRON = {
    "0.9": True
}

def schematron_for_version(version):
    path = schematron_for_version_unsafe(version)
    if isinstance(path, ValueError):
        raise path  # pylint: disable=raising-bad-type

    return path


def schematron_for_version_unsafe(version):
    # Some version do not have a schematron check. Testing the
    # presence of a path and assume that an absent file means we don't
    # expect a schematron check is error prone, ergo this check:
    if version in _NO_SCHEMATRON:
        return None

    path = os.path.join(schemas_dirname, "out/btw-storage-%s.xsl" % version)

    if not os.path.exists(path):
        path = ValueError("missing schematron version: " + version)

    return path


# 20140912: No longer needed as part of normal operations but we are
# keeping it here in case some old data needs conversion. It should
# probably be removed after a few versions of BTW have been released.


def editable_to_storage(data):
    return util.run_saxon(os.path.join(xsl_dirname, "out/html-to-xml.xsl"),
                          data)


def clean_xml(data):
    return util.run_saxon(os.path.join(xsl_dirname, "xml-to-xml.xsl"),
                          data)


class XMLTree(object):

    def __init__(self, data):
        """
The XML tree representation of the data. Allows performing operations
on this tree or querying it.

:param data: The data to parse.
:type data: str
"""
        self.parsing_error = None
        self.tree = None
        try:
            self.tree = lxml.etree.fromstring(data)
        except lxml.etree.XMLSyntaxError as ex:
            self.parsing_error = "Parsing error: " + str(ex)

    def is_data_unclean(self):
        """
Ensure that the tree parses as XML.

:returns: Evaluates to False if the tree is clean, True if not. When
          unclean the value returned is a diagnosis message.
    """
        if self.parsing_error:
            return self.parsing_error

        return False

    def get_bibilographical_targets(self):
        """
Get all targets that point to bibliographical references.

:returns: The targets.
:rtype: :class:`set` of strings.
"""
        refs = self.tree.xpath("//tei:ref",
                               namespaces={
                                   'tei': 'http://www.tei-c.org/ns/1.0'
                               })

        return set([target for target in
                    [ref.get('target') for ref in refs]
                    if target.startswith('/bibliography/')])

    def extract_lemma(self):
        """
Extracts the lemma from the XML tree. This is the contents of the
btw:lemma element.

:returns: The lemma.
:rtype: str
"""
        lemma = self.tree.xpath(
            "btw:lemma",
            namespaces={
                'btw': 'http://mangalamresearch.org/ns/btw-storage'})

        if not len(lemma):
            return None

        lemma = lemma[0].text

        if lemma is None:
            return None

        lemma = lemma.strip()

        if len(lemma) == 0:
            return None

        return lemma

    def extract_authority(self):
        """
Extracts the authority from the XML tree. This is the contents of the
authority attribute on the top element.

:returns: The authority
:rtype: str
"""
        authority = self.tree.get('authority')

        if authority is None:
            raise ValueError("can't find the authority in the data passed")

        return authority.strip()

    def extract_version(self):
        """
Extracts the version from the XML tree.

:returns: The version
:rtype: str
"""
        version = self.extract_version_unsafe()
        if version is None:
            raise ValueError("can't find the version in the data passed")

        return version

    def extract_version_unsafe(self):
        """
        Extracts the version from the XML tree.

:returns: The version, if it is present. ``None`` if the version is
          not present.
:rtype: str
        """
        version = self.tree.get('version')
        return version.strip() if version is not None else None


_auth_re = re.compile(r'authority\s*=\s*(["\']).*?\1')
_new_auth_re = re.compile(r"^[A-Za-z0-9/]*$")


def set_authority(data, new_authority):
    # We don't use lxml for this because we don't want to introduce
    # another serialization in the pipe which may change things in
    # unexpected ways.
    if not _new_auth_re.match(new_authority):
        raise ValueError("the new authority contains invalid data")
    return _auth_re.sub('authority="{0}"'.format(new_authority), data, count=1)


def xhtml_to_xml(data):
    return data.replace(u"&nbsp;", u'\u00a0')

#  LocalWords:  xml html xsl xhtml xmlns btw lxml r'authority Za nbsp
