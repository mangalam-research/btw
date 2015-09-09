"""XML parsing and conversion utilities.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import lxml.etree

import os
import re
from collections import OrderedDict, namedtuple

import semver

import lib.util as util

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")
xsl_dirname = os.path.join(dirname, "../utils/xsl/")
mods_schema_path = os.path.join(schemas_dirname, "out/flat_mods/mods-3-5.xsd")

tei_namespace = 'http://www.tei-c.org/ns/1.0'
btw_namespace = 'http://mangalamresearch.org/ns/btw-storage'

default_namespace_mapping = {
    'btw': btw_namespace,
    'tei': tei_namespace
}

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

VersionInfo = namedtuple('VersionInfo', ('can_revert', 'can_validate'))

schema_dir_re = re.compile(r"^btw-storage-([0-9.]+)$")
_supported_schema_versions = None
def get_supported_schema_versions():
    """
    Returns a list of schema versions that we support.
    """
    global _supported_schema_versions  # pylint: disable=global-statement

    if _supported_schema_versions is not None:
        return _supported_schema_versions

    versions = []
    outdir = os.path.join(schemas_dirname, "out")
    for d in (d for d in os.listdir(outdir)
              if os.path.isdir(os.path.join(outdir, d))):
        match = schema_dir_re.match(d)
        if match:
            version = match.group(1)
            versions.append(version)

    # We don't actually always have the patch number that semver
    # expects, so normalize.
    norm = lambda x: (x + ".0") if x.count(".") == 1 else x

    versions = sorted(versions, lambda a, b: semver.compare(norm(a),
                                                            norm(b)))

    # We support validating all versions that we find but we can
    # revert only to the last one.
    ret = OrderedDict()
    for v in versions[:-1]:
        ret[v] = VersionInfo(can_validate=True, can_revert=False)

    ret[versions[-1]] = VersionInfo(can_validate=True, can_revert=True)

    _supported_schema_versions = ret

    return ret

def can_revert_to(version):
    """
    :param version: The version to check.
    :type version: `:class:str`
    :returns: ``True`` if we can revert to ``version``, ``False``
              otherwise.
    """
    info = get_supported_schema_versions().get(version, None)
    return info is not None and info.can_revert


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


def convert_to_version(data, fr, to):
    xsl_file_name = "btw-storage-{0}-to-{1}.xsl".format(fr, to)
    xsl_path = os.path.join(schemas_dirname, xsl_file_name)
    if not os.path.exists(xsl_path):
        raise ValueError("cannot convert from {0} to {1}".format(fr, to))

    return util.run_saxon(xsl_path, data)


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
                               namespaces=default_namespace_mapping)

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
        lemma = self.tree.xpath("btw:lemma",
                                namespaces=default_namespace_mapping)

        if not len(lemma):
            return None

        lemma = lemma[0].text

        if lemma is None:
            return None

        lemma = lemma.strip()

        if len(lemma) == 0:
            return None

        return lemma

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


_auth_re = re.compile(r' authority\s*=\s*(["\']).*?\1')

def delete_authority(data):
    # We don't use lxml for this because we don't want to introduce
    # another serialization in the pipe which may change things in
    # unexpected ways.
    return _auth_re.sub('', data, count=1)

_version_re = re.compile(r'(<btw:entry\s+.*?)version\s*=\s*(["\']).*?\2')
_new_version_re = re.compile(r"^[0-9.]+$")


def set_version(data, new_version):
    # We don't use lxml for this because we don't want to introduce
    # another serialization in the pipe which may change things in
    # unexpected ways.
    if not _new_version_re.match(new_version):
        raise ValueError("the new version contains invalid data")
    ret = _version_re.sub(r'\1version="{0}"'.format(new_version),
                          data, count=1)
    if ret == data:
        raise ValueError("was unable to set new version")
    return ret


def xhtml_to_xml(data):
    return data.replace(u"&nbsp;", u'\u00a0')

#  LocalWords:  xml html xsl xhtml xmlns btw lxml r'authority Za nbsp
