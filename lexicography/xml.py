"""XML parsing and conversion utilities.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
import lxml.etree

import os
import re

import util

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")
xsl_dirname = os.path.join(dirname, "../utils/xsl/")

def storage_to_editable(data):
    return util.run_saxon(os.path.join(xsl_dirname, "out/xml-to-html.xsl"),
                          data)

def editable_to_storage(data):
    return util.run_saxon(os.path.join(xsl_dirname, "out/html-to-xml.xsl"),
                          data)

class XMLTree(object):
    def __init__(self, data):
        """
The XML tree represetation of the data. Allows performing operations
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
Ensure that the tree parses as XML and that it contains only div
elements in the ``http://www.w3.org/1999/xhtml`` namespace, no
processing instructions, no attributes in any namespace and no
attribute other than ``class`` or ``data-wed-*``.

:returns: Evaluates to False if the tree is clean, True if not. When unclean the value returned is a diagnosis message.

.. warning:: This method is security-critical. In theory it would be
    possible for one user of the system to include JavaScript in the
    data they send to BTW. This JavaScript could then be loaded in
    someone else's browser and executed there.
    """
        if self.parsing_error:
            return self.parsing_error

        for node in self.tree.iter():
            # pylint: disable-msg=W0212
            if isinstance(node, lxml.etree._ProcessingInstruction):
                return "Processing instruction found."
            elif isinstance(node, lxml.etree._Element):
                if node.tag != "{http://www.w3.org/1999/xhtml}div":
                    return "Element outside the xhtml namespace: " + node.tag
                for attr in node.attrib.keys():
                    if attr == "xmlns":
                        if node.attrib[attr] != "http://www.w3.org/1999/xhtml":
                            return ("Attribute xmlns with invalid value: " +
                                    node.attrib[attr] + ".")
                    elif attr != "class" and not attr.startswith("data-wed-"):
                        return "Invalid attribute: " + attr + "."

        return False

    def extract_headword(self):
        """
Extracts the headword from the XML tree. This is the contents of the
btw:lemma element.

:returns: The headword.
:rtype: str
"""
        class_sought = 'btw:lemma'
        lemma = self.tree.xpath(
            "xhtml:div[contains(@class, '" + class_sought + "')]",
            namespaces={
                'xhtml':
                'http://www.w3.org/1999/xhtml'})

        # Check that it is really what we want. Unfortunately writing the
        # XPath 1.0 (what lxml supports) required to do a good job at
        # tokenizing @class would be hairier than just doing it in python.
        if len(lemma):
            classes = lemma[0].get("class").strip().split()
            if not any(x == class_sought for x in classes):
                lemma = [] # Not what we wanted after all

        if not len(lemma):
            raise ValueError("can't find a headword in the data passed")

        return lemma[0].text

    def extract_authority(self):
        """
Extracts the authority from the XML tree. This is the contents of the
authority attribute on the top element.

:returns: The authority
:rtype: str
"""
        authority = self.tree.get('data-wed-authority')

        if authority is None:
            raise ValueError("can't find the authority in the data passed")

        return authority.strip()

auth_re = re.compile(r'authority\s*=\s*(["\']).*?\1')
new_auth_re = re.compile(r"^[A-Za-z0-9/]*$")
def set_authority(data, new_authority):
    # We don't use lxml for this because we don't want to introduce
    # another serialization in the pipe which may change things in
    # unexpected ways.
    if not new_auth_re.match(new_authority):
        raise ValueError("the new authority contains invalid data")
    return auth_re.sub('authority="{0}"'.format(new_authority), data, count=1)

def xhtml_to_xml(data):
    return data.replace(u"&nbsp;", u'\u00a0')
