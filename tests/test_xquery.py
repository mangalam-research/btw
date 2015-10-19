from unittest import TestCase

from lib import xquery

class _BuilderTest(TestCase):

    def test_make(self):
        "``make`` should return a properly formatted XQuery."
        self.assertEqual(self.builder.make("foo"), """\
xquery version '3.0';
declare namespace btw = 'http://mangalamresearch.org/ns/btw-storage';
foo""")

    def test_format(self):
        "``format`` should quote strings."
        self.assertEqual(self.builder.format("{foo}",
                                             foo="q"), """\
xquery version '3.0';
declare namespace btw = 'http://mangalamresearch.org/ns/btw-storage';
"q\"""")

    def test_format_escapes(self):
        "``format`` should escape double quotes in strings."
        self.assertEqual(self.builder.format("{foo}",
                                             foo='foo "bar"'), """\
xquery version '3.0';
declare namespace btw = 'http://mangalamresearch.org/ns/btw-storage';
"foo &#34;bar&#34;\"""")

    def test_format_verbatim(self):
        "``format`` should insert ``Verbatim`` objects verbatim."
        self.assertEqual(self.builder.format(
            "{foo}",
            foo=xquery.Verbatim('foo "bar"')), """\
xquery version '3.0';
declare namespace btw = 'http://mangalamresearch.org/ns/btw-storage';
foo "bar\"""")

    def test_format_verbatim_braces(self):
        """
        ``format`` should  ``Verbatim`` objects verbatim, even with braces.
        ]"""
        self.assertEqual(self.builder.format(
            "{foo}",
            foo=xquery.Verbatim('{blah}')), """\
xquery version '3.0';
declare namespace btw = 'http://mangalamresearch.org/ns/btw-storage';
{blah}""")

class XQueryBuilderTest(_BuilderTest):
    """
    Test the XQueryBuilder object.
    """

    def setUp(self):
        self.builder = xquery.XQueryBuilder()
        return super(XQueryBuilderTest, self).setUp()

class DefaultBuilderTest(_BuilderTest):
    """
    Test the default builder used by the top level functions in the xquery
    module.
    """

    def setUp(self):
        self.builder = xquery
        return super(DefaultBuilderTest, self).setUp()
