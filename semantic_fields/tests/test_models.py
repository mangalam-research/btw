import re

from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.html import escape

from ..models import SemanticField, SpecifiedSemanticField
from ..util import ParsedExpression
from lib.testutil import wipd

sep_re = re.compile(r"(\s+(?:>|::)\s+)")
pos_re = re.compile(r" \((.*)\)$")

def to_str(path):
    return "@".join(unicode(x) for x in path)

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SemanticFieldTestCase(TestCase):

    def test_parsed_path(self):
        """
        Test that ``parsed_path`` returns a proper value when ``path``
        changes.
        """
        c = SemanticField(path="01.01n")
        self.assertEqual(to_str(c.parsed_path), "01.01n")
        c.path = "01.01v"
        self.assertEqual(to_str(c.parsed_path), "01.01v")

    def test_pos(self):
        """
        Test that ``pos`` returns a proper value when ``path`` changes.
        """
        c = SemanticField(path="01.01n")
        self.assertEqual(unicode(c.pos), "n")
        c.path = "01.01v"
        self.assertEqual(unicode(c.pos), "v")

    def test_verbose_pos(self):
        """
        Test that ``verbose_pos`` returns a proper value when ``path``
        changes.
        """
        c = SemanticField(path="01.01n")
        self.assertEqual(unicode(c.verbose_pos), "Noun")
        c.path = "01.01v"
        self.assertEqual(unicode(c.verbose_pos), "Verb")

    def test_is_subcat(self):
        """
        Test that ``is_subcat`` returns a proper value when ``path``
        changes.
        """
        c = SemanticField(path="01.01|01n")
        self.assertTrue(c.is_subcat)
        c.path = "01.01v"
        self.assertFalse(c.is_subcat)

    def test_heading_and_pos(self):
        """
        Test that ``heading_and_pos`` returns a proper value when ``path``
        changes.
        """
        c = SemanticField(path="01.01n", heading="foo")
        self.assertEqual(unicode(c.heading_and_pos), "foo (Noun)")
        c.path = "01.01v"
        self.assertEqual(unicode(c.heading_and_pos), "foo (Verb)")

    def test_related_by_pos(self):
        """
        Test that related_by_pos returns a proper value when ``path``
        changes.
        """

        # This test hits the database, but we create the data we need
        # here rather than load from a fixture, which would be
        # expensive.

        base_path = "01.01"
        create_related = ("n", "v", "aj", "av")
        for pos in create_related:
            c = SemanticField(path=base_path + pos, heading="foo " + pos)
            c.save()

        c = SemanticField.objects.get(path=base_path + "n")

        related = [x.id for x in c.related_by_pos]

        expected = [SemanticField.objects.get(path=base_path + pos).id
                    for pos in create_related if pos != "n"]
        self.assertTrue(len(related) > 0)
        self.assertTrue(len(expected) > 0)
        self.assertItemsEqual(related, expected)

        # We now change the path to a value that has no related records.
        c.path = "02.02n"
        self.assertEqual(len(c.related_by_pos), 0)

    def test_possible_new_poses_custom(self):
        """
        Test that possible_new_posses has a correct value when the field
        is custom.
        """

        # This test hits the database, but we create the data we need
        # here rather than load from a fixture, which would be
        # expensive.
        base_path = "01.01"
        create_related = ("n", "v", "aj", "av")
        for pos in create_related:
            c = SemanticField(path=base_path + pos, heading="foo " + pos)
            c.save()

        c = SemanticField.objects.get(path=base_path + "n")

        self.assertItemsEqual(
            c.possible_new_poses,
            ('', 'cj', 'in', 'p', 'ph', 'vi', 'vm', 'vp', 'vr', 'vt'))

    def test_possible_new_poses_hte(self):
        """
        Test that possible_new_posses has a correct value when the field
        is not custom.
        """

        # This test hits the database, but we create the data we need
        # here rather than load from a fixture, which would be
        # expensive.
        base_path = "01.01"
        create_related = ("n", "v", "aj", "av")
        catid = 333
        for pos in create_related:
            c = SemanticField(path=base_path + pos, heading="foo " + pos,
                              catid=catid)
            c.save()
            catid += 1

        c = SemanticField.objects.get(path=base_path + "n")

        self.assertItemsEqual(c.possible_new_poses, set())

    def test_link(self):
        """
        Test that the value of ``link`` is correct.
        """
        c = SemanticField(path="01.01n", heading="foo")
        c.save()
        self.assertEqual(c.link,
                         ("<a class='btn btn-default btn-sm sf-link' "
                          "href='/en-us/semantic_fields/semanticfield/{0}/'>"
                          "foo</a>").format(c.id))

    def test_make_link_default(self):
        """
        ``make_link`` should return a reasonable default.
        """
        c = SemanticField(path="01.01n", heading="foo")
        c.save()
        self.assertEqual(c.make_link(),
                         ("<a class='btn btn-default btn-sm sf-link' "
                          "href='/en-us/semantic_fields/semanticfield/{0}/'>"
                          "foo</a>").format(c.id))

    def test_make_link_text(self):
        """
        ``make_link`` should honor the ``text`` parameter.
        """
        c = SemanticField(path="01.01n", heading="foo")
        c.save()
        self.assertEqual(c.make_link("bar"),
                         ("<a class='btn btn-default btn-sm sf-link' "
                          "href='/en-us/semantic_fields/semanticfield/{0}/'>"
                          "bar</a>").format(c.id))

    def test_make_link_css_class(self):
        """
        ``make_link`` should honor the ``css_class`` parameter.
        """
        c = SemanticField(path="01.01n", heading="foo")
        c.save()
        self.assertEqual(c.make_link(css_class="bar"),
                         ("<a class='btn btn-default btn-sm sf-link bar' "
                          "href='/en-us/semantic_fields/semanticfield/{0}/'>"
                          "foo</a>").format(c.id))

    def test_breadcrumbs_parent_mixed(self):
        """
        ``breadcrumbs`` should have a correct value.
        """
        specs = (
            ("01n", "baz", "baz (Noun)"),
            ("01.01n", "foo", "baz > foo (Noun)"),
            ("01.01.01n", "bar", "baz > foo > bar (Noun)"),
            ("01.01.01|01n", "bwip", "baz > foo > bar :: bwip (Noun)"),
            ("01.01.01|01.01n", "toto",
             "baz > foo > bar :: bwip :: toto (Noun)")
        )
        for (path, heading, expected) in specs:
            parent_path = ParsedExpression(path).parent()
            parent = None
            if parent_path is not None:
                try:
                    parent = SemanticField.objects.get(
                        path=unicode(parent_path))
                except SemanticField.DoesNotExist:
                    pass

            cat = SemanticField(path=path, heading=heading, parent=parent)
            cat.save()
            self.assertEqual(cat.breadcrumbs, escape(expected))

    def test_linked_breadcrumbs_parent_mixed(self):
        """
        ``linked_breadcrumbs`` should have a correct value.
        """
        specs = (
            ("01n", "baz", "baz (Noun)"),
            ("01.01n", "foo", "baz > foo (Noun)"),
            ("01.01.01n", "bar", "baz > foo > bar (Noun)"),
            ("01.01.01|01n", "bwip", "baz > foo > bar :: bwip (Noun)"),
            ("01.01.01|01.01n", "toto",
             "baz > foo > bar :: bwip :: toto (Noun)")
        )
        for (path, heading, expected) in specs:
            parent_path = ParsedExpression(path).parent()
            parent = None
            if parent_path is not None:
                try:
                    parent = SemanticField.objects.get(
                        path=unicode(parent_path))
                except SemanticField.DoesNotExist:
                    pass

            cat = SemanticField(path=path, heading=heading, parent=parent)
            cat.save()

            # We don't want to hardcode the actual links in
            # ``expected`` so we parse what we have now and modify it
            # to add links. The link value have been tested by other
            # tests.
            parts = sep_re.split(expected)
            expected = "".join(
                [(escape(p) if sep_re.match(p) else
                  SemanticField.objects.get(heading=p).link)
                 for p in parts[:-1]])

            last = SemanticField.objects.get(
                heading=pos_re.sub('', parts[-1]))
            expected += last.make_link(last.heading_and_pos)
            expected = '<span class="sf-breadcrumbs">' + expected + \
                       '</span>'

            self.assertEqual(cat.linked_breadcrumbs, expected)

    def test_hte_url_on_non_hte_semanticfield(self):
        """
        ``hte_url`` should be ``None`` on non-HTE categories.
        """
        c = SemanticField(path="01.01n")
        self.assertIsNone(c.hte_url)

    def test_hte_url_on_hte_semanticfield(self):
        """
        ``hte_url`` should have a decent value for HTE categories.
        """
        c = SemanticField(path="01.01n", catid=1)
        self.assertEqual(
            c.hte_url,
            "http://historicalthesaurus.arts.gla.ac.uk/category/?id=1")

    def test_make_child_hte_field(self):
        """
        ``make_child`` on a HTE field should open a new branch
        """
        c = SemanticField(path="01.01n")
        c.save()
        child = c.make_child("foo", "n")
        self.assertEqual(child.path, "01.01n/1n")
        self.assertEqual(child.heading, "foo")
        self.assertEqual(child.parent, c)
        self.assertEqual(child.catid, None)

    def test_make_child_non_hte_field(self):
        """
        ``make_child`` on a custom field should just add to the branch.
        """
        c = SemanticField(path="01.01n/1n")
        c.save()
        child = c.make_child("foo", "n")
        self.assertEqual(child.path, "01.01n/1.1n")
        self.assertEqual(child.heading, "foo")
        self.assertEqual(child.parent, c)
        self.assertEqual(child.catid, None)

    def test_make_child_twice(self):
        """
        ``make_child`` called twice on the same field will create fields
        with paths that do no conflict.
        """
        c = SemanticField(path="01.01n")
        c.save()
        child = c.make_child("foo", "n")
        self.assertEqual(child.path, "01.01n/1n")
        self.assertEqual(child.heading, "foo")
        self.assertEqual(child.parent, c)
        self.assertEqual(child.catid, None)

        child = c.make_child("bar", "n")
        self.assertEqual(child.path, "01.01n/2n")
        self.assertEqual(child.heading, "bar")
        self.assertEqual(child.parent, c)
        self.assertEqual(child.catid, None)

    def test_make_child_bad_pos(self):
        """
        ``make_child`` with a bad pos fails.
        """
        c = SemanticField(path="01.01n")
        c.save()
        with self.assertRaisesRegexp(ValueError,
                                     "^pos is not among valid choices$"):
            c.make_child("foo", "x")

    def test_make_related_by_pos_non_custom(self):
        """
        ``make_related_by_pos`` with non-custom field fails.
        """
        c = SemanticField(path="01.01n")
        c.save()
        with self.assertRaisesRegexp(
                ValueError,
                "^cannot make a field related by pos for a non-custom field$"):
            c.make_related_by_pos("foo", "a")

    def test_make_related_by_pos_bad_pos(self):
        """
        ``make_related_by_pos`` with a bad pos value fails.
        """
        c = SemanticField(path="01.01n/1n")
        c.save()
        with self.assertRaisesRegexp(
                ValueError,
                "^pos is not among valid choices$"):
            c.make_related_by_pos("foo", "invalid")

    def test_make_related_by_pos_same_pos(self):
        """
        ``make_related_by_pos`` with a pos which is the same as the
        original fails.
        """
        c = SemanticField(path="01.01n/1n")
        c.save()
        with self.assertRaisesRegexp(
                ValueError,
                "^trying to make a field related by pos with the same "
                "pos as the original$"):
            c.make_related_by_pos("foo", "n")

    def test_make_related_by_pos(self):
        """
        ``make_related_by_pos`` returns a good value.
        """
        c = SemanticField(path="01.01n/1n")
        c.save()
        rel = c.make_related_by_pos("foo", "v")
        self.assertEqual(rel.path, "01.01n/1v")
        self.assertEqual(rel.heading, "foo")
        self.assertEqual(rel.parent, c.parent)
        self.assertEqual(rel.catid, None)


@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SpecifiedSemanticFieldTestCase(TestCase):

    def test_pos(self):
        """
        Test that ``pos`` returns a proper value when ``path`` changes.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        self.assertEqual(unicode(c.pos), "n")
        c.path = "01.01v@01.02n"
        self.assertEqual(unicode(c.pos), "v")

    def test_verbose_pos(self):
        """
        Test that ``verbose_pos`` returns a proper value when ``path``
        changes.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        self.assertEqual(c.verbose_pos, "Noun")
        c.path = "01.01v@01.02n"
        self.assertEqual(c.verbose_pos, "Verb")

    def test_is_subcat(self):
        """
        Test that ``is_subcat`` returns ``False`` even if the participating
        fields are subcats.
        """
        c = SpecifiedSemanticField(path="01.01|01n@01.02|02v")
        self.assertFalse(c.is_subcat)

    def test_heading_and_pos(self):
        """
        Test that ``heading_and_pos`` returns a proper value when ``path``
        changes.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v", heading="foo")
        self.assertEqual(unicode(c.heading_and_pos), "foo (Noun)")
        c.path = "01.01v@01.02n"
        self.assertEqual(unicode(c.heading_and_pos), "foo (Verb)")

    def test_related_by_pos(self):
        """
        Test that related_by_pos returns en empty set.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v", heading="foo")
        self.assertEqual(len(c.related_by_pos), 0)

    def test_possible_new_poses(self):
        """
        Test that ``possible_new_poses`` is empty.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v", heading="foo")
        self.assertEqual(len(c.possible_new_poses), 0)

    def test_hte_url(self):
        """
        ``hte_url`` should be ``None``.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        self.assertIsNone(c.hte_url)

    def test_save_raises(self):
        """
        ``save`` raises an exception.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        with self.assertRaisesRegexp(Exception,
                                     "cannot save a specified semantic field"):
            c.save()

    def test_make_child_raises(self):
        """
        ``make_child`` raises an exception.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        with self.assertRaisesRegexp(Exception,
                                     "cannot make a child of a "
                                     "SpecifiedSemanticField"):
            c.make_child("foo", "n")

    def test_make_related_by_pos_raises(self):
        """
        ``make_child`` raises an exception.
        """
        c = SpecifiedSemanticField(path="01.01n@01.02v")
        with self.assertRaisesRegexp(Exception,
                                     "cannot make a related field for a "
                                     "SpecifiedSemanticField"):
            c.make_related_by_pos("foo", "n")

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SemanticFieldTransactionTestCase(TransactionTestCase):

    def test_make_related_by_pos_duplicate(self):
        """
        ``make_related_by_pos`` fails when trying to create a duplicate.
        """
        c = SemanticField(path="01.01n/1n")
        c.save()
        c.make_related_by_pos("foo", "v")
        with self.assertRaisesRegexp(
                ValueError,
                "^There is already a semantic field in the BTW namespace "
                "with pos 'v'.$"):
            c.make_related_by_pos("bar", "v")

    def test_make_child_duplicate(self):
        """
        ``make_child`` does not allow creating duplicate children.
        """
        c = SemanticField(path="01.01n")
        c.save()
        c.make_child("foo", "n")

        with self.assertRaisesRegexp(
                ValueError,
                "^There is already a semantic field in the BTW namespace "
                "with pos 'n' and heading 'foo'.$"):
            c.make_child("foo", "n")

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SemanticFieldManagerTestCase(TestCase):

    def test_make_field_bad_pos(self):
        """
        ``make_field`` with a bad pos fails.
        """
        with self.assertRaisesRegexp(ValueError,
                                     "^pos is not among valid choices$"):
            SemanticField.objects.make_field("foo", "invalid")

    def test_make_field(self):
        """
        ``make_field`` returns a good value.
        """
        field = SemanticField.objects.make_field("foo", "n")
        self.assertEqual(field.path, "/1n")
        self.assertFalse(isinstance(field.path, ParsedExpression))
        self.assertEqual(field.heading, "foo")
        self.assertEqual(field.parent, None)
        self.assertEqual(field.catid, None)

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SemanticFieldManagerTransactionTestCase(TestCase):

    def test_make_field_duplicate(self):
        """
        ``make_child`` does not allow creating duplicate root fields.
        """
        SemanticField.objects.make_field("foo", "n")
        with self.assertRaisesRegexp(
                ValueError,
                "^There is already a semantic field in the BTW namespace "
                "with pos 'n' and heading 'foo'.$"):
            SemanticField.objects.make_field("foo", "n")
