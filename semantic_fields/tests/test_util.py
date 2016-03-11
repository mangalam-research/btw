from django.test import TestCase
from grako.exceptions import FailedParse

from ..util import parse_local_reference, ParsedExpression, POS_CHOICES, \
    POS_CHOICES_EXPANDED

class UtilTestCase(TestCase):
    # We specifically do not test the failure modes of parse_sf
    # because parse_sf is not designed to **validate** the semantic
    # field codes. We want it to fail if it cannot perform its job,
    # but *how* it fails is not part of the specification, and what
    # precisely causes it to fail is also not part of the spec. In
    # fact, it would be okay for it to do garbage-in/garbage-out.

    def test_parse_local_reference_strips_whitespace(self):
        """
        ``parse_local_reference`` should strip whitespace at the start and
        end of the codes passed to it.
        """
        parsed = parse_local_reference("  \t03.07n\r  ")
        self.assertEqual(parsed.hte_levels, ("03", "07"))
        self.assertEqual(parsed.hte_subcats, None)
        self.assertEqual(parsed.hte_pos, "n")

    def test_parse_local_reference_fails_on_specification(self):
        """
        ``parse_local_reference`` fails if there is a specification on the
        reference.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^references cannot have specifications$"):
            parse_local_reference("03.07n@01n")

    def test_parse_local_reference_fails_on_multiple_branches(self):
        """
        ``parse_local_reference`` fails if there is more than one branch.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^BTW currently supports only one branch$"):
            parse_local_reference("03.07n/1.1n/1.2n")

    def test_parse_local_reference_fails_on_more_than_two_levels(self):
        """
        ``parse_local_reference`` fails if there is more than two levels
        in a single branch.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^BTW does not allow branches with "
                "more than two levels$"):
            parse_local_reference("03.07n/1.1.1n")

    def test_parse_local_reference_fails_on_url(self):
        """
        ``parse_local_reference`` fails if there is a branch with a URI.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^BTW does not allow branches with URIs$"):
            parse_local_reference("03.07n/{foo}1.1n")

    def test_parse_local_reference_fails_on_empty_string(self):
        """
        ``parse_local_reference`` fails if the string is empty.
        """
        with self.assertRaises(FailedParse):
            parse_local_reference("")

    def test_parse_local_reference_fails_on_junk(self):
        "Junk causes a parsing error."
        with self.assertRaises(FailedParse):
            parse_local_reference("abcd")

class ParsedExpressionTest(TestCase):

    def test_only_hte(self):
        """
        Can parse the HTE part of a semantic field reference.
        """
        parsed = ParsedExpression("01.01|02.03n")
        self.assertEqual(parsed.hte_levels, ("01", "01"))
        self.assertEqual(parsed.hte_subcats, ("02", "03"))
        self.assertEqual(parsed.hte_pos, "n")
        self.assertEqual(parsed.branches, None)
        self.assertEqual(parsed.specification, None)
        self.assertEqual(parsed.pos, "n")
        self.assertEqual(parsed.last_uri, None)

    def test_branches(self):
        """
        Can parse a reference with branches.
        """
        parsed = ParsedExpression("01.01n"
                                  "/{http://www.foo.com}1.2.3v"
                                  "/{http://www.bar.com}4.5aj")
        self.assertEqual(parsed.hte_levels, ("01", "01"))
        self.assertEqual(parsed.hte_subcats, None)
        self.assertEqual(parsed.hte_pos, "n")
        self.assertEqual(parsed.specification, None)

        self.assertEqual(len(parsed.branches), 2)
        self.assertEqual(parsed.branches[0].uri, "http://www.foo.com")
        self.assertEqual(parsed.branches[0].levels, ("1", "2", "3"))
        self.assertEqual(parsed.branches[0].pos, "v")

        self.assertEqual(parsed.branches[1].uri, "http://www.bar.com")
        self.assertEqual(parsed.branches[1].levels, ("4", "5"))
        self.assertEqual(parsed.branches[1].pos, "aj")
        self.assertEqual(parsed.pos, "aj")
        self.assertEqual(parsed.last_uri, "http://www.bar.com")

    def test_specifications(self):
        """
        Can parse a reference with specifications.
        """
        parsed = ParsedExpression("01.01n"
                                  "/{http://www.foo.com}1.2.3v"
                                  "/{http://www.bar.com}4.5aj"
                                  "@01.02n@04.05n")

        self.assertEqual(parsed.hte_levels, ("01", "01"))
        self.assertEqual(parsed.hte_subcats, None)
        self.assertEqual(parsed.hte_pos, "n")
        self.assertEqual(parsed.last_uri, "http://www.bar.com")

        self.assertEqual(len(parsed.branches), 2)
        self.assertEqual(parsed.branches[0].uri, "http://www.foo.com")
        self.assertEqual(parsed.branches[0].levels, ("1", "2", "3"))
        self.assertEqual(parsed.branches[0].pos, "v")

        self.assertEqual(parsed.branches[1].uri, "http://www.bar.com")
        self.assertEqual(parsed.branches[1].levels, ("4", "5"))
        self.assertEqual(parsed.branches[1].pos, "aj")

        self.assertEqual(parsed.specification.hte_levels, ("01", "02"))
        self.assertEqual(parsed.specification.hte_subcats, None)
        self.assertEqual(parsed.specification.hte_pos, "n")
        self.assertEqual(parsed.specification.branches, None)
        self.assertEqual(parsed.specification.last_uri, None)

        specspec = parsed.specification.specification
        self.assertEqual(specspec.hte_levels, ("04", "05"))
        self.assertEqual(specspec.hte_subcats, None)
        self.assertEqual(specspec.hte_pos, "n")
        self.assertEqual(specspec.branches, None)
        self.assertEqual(specspec.last_uri, None)
        self.assertEqual(specspec.specification, None)

    def test_start_branches(self):
        """
        Can parse a reference which starts with a branch.
        """
        parsed = ParsedExpression("/{http://www.foo.com}1.2.3v")
        self.assertEqual(parsed.hte_levels, None)
        self.assertEqual(parsed.hte_subcats, None)
        self.assertEqual(parsed.hte_pos, None)
        self.assertEqual(len(parsed.branches), 1)
        self.assertEqual(parsed.branches[0].uri, "http://www.foo.com")
        self.assertEqual(parsed.branches[0].levels, ("1", "2", "3"))
        self.assertEqual(parsed.branches[0].pos, "v")
        self.assertEqual(parsed.specification, None)
        self.assertEqual(parsed.pos, "v")
        self.assertEqual(parsed.last_uri, "http://www.foo.com")

    def test_subcat_parent(self):
        """
        Can find the parent of a field with subcat.
        """
        parsed = ParsedExpression("01.01|02.03n")
        expected_values = [
            "01.01|02n",
            "01.01n",
            "01n",
        ]
        parent = parsed
        for value in expected_values:
            parent = parent.parent()
            self.assertEqual(str(parent), value)
        parent = parent.parent()
        self.assertIsNone(parent)

    def test_branch_parent(self):
        """
        Can find the parent of a field with subcat.
        """
        parsed = ParsedExpression("01.01|02.03n"
                                  "/{http://www.foo.com}1.2.3v"
                                  "/{http://www.bar.com}4.5aj")

        expected_values = [
            "01.01|02.03n/{http://www.foo.com}1.2.3v"
            "/{http://www.bar.com}4aj",
            "01.01|02.03n/{http://www.foo.com}1.2.3v",
            "01.01|02.03n/{http://www.foo.com}1.2v",
            "01.01|02.03n/{http://www.foo.com}1v",
            "01.01|02.03n",
            "01.01|02n",
            "01.01n",
            "01n",
        ]
        parent = parsed
        for value in expected_values:
            parent = parent.parent()
            self.assertEqual(str(parent), value)
        parent = parent.parent()
        self.assertIsNone(parent)

    def test_pos_specified(self):
        """
        ``pos`` raises an exception on specified expressions.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^cannot determine the pos of a "
                "specified reference$"):
            # pylint: disable=expression-not-assigned
            ParsedExpression("01.01|02.03n/04.05n@01.01n").pos

    def test_related_by_pos_hte_field(self):
        """
        ``related_by_pos()`` should return a correct list of related paths
        when called for a HTE field.
        """
        parsed = ParsedExpression("01.01|02.03n")
        related = [unicode(x) for x in parsed.related_by_pos()]
        self.assertItemsEqual(related, ("01.01|02.03" + x for (x, _) in
                                        POS_CHOICES if x != "n"))
        # Specifically check that a path without pos is not there.
        self.assertNotIn("01.01|02.03", related)

    def test_related_by_pos_branch(self):
        """
        ``related_by_pos()`` should return a correct list of related paths
        when called on an expression with branches.
        """
        parsed = ParsedExpression("01.01|02.03n/04.05n")
        related = [unicode(x) for x in parsed.related_by_pos()]
        self.assertItemsEqual(related, ("01.01|02.03n/04.05" + x for (x, _) in
                                        POS_CHOICES_EXPANDED if x != "n"))
        # Specifically check that a path without pos *is* there.
        self.assertIn("01.01|02.03n/04.05", related)

    def test_related_by_pos_specified(self):
        """
        ``related_by_pos()`` raises an exception on specified expressions.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^cannot determine the related expressions of a "
                "specified reference$"):
            ParsedExpression("01.01|02.03n/04.05n@01.01n").related_by_pos()

    def test_last_level_number_hte(self):
        """
        ``last_level_number`` provide the right number on pure HTE
        expressions without subcategories.
        """
        parsed = ParsedExpression("01.02.03.04n")
        self.assertEqual(parsed.last_level_number, 4)

    def test_last_level_number_hte_subcat(self):
        """
        ``last_level_number`` provide the right number on pure HTE
        expressions with subcategories.
        """
        parsed = ParsedExpression("01.01|01.02n")
        self.assertEqual(parsed.last_level_number, 2)

    def test_last_level_number_branches(self):
        """
        ``last_level_number`` provide the right number on expressions with
        branches.
        """
        parsed = ParsedExpression("01.01n/01.02n/03.06n")
        self.assertEqual(parsed.last_level_number, 6)

    def test_last_level_number_fails_on_specified(self):
        """
        ``last_level_number`` raise an exception when used on a specified
        expression.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^cannot determine the last level of a "
                "specified reference$"):
            # pylint: disable=expression-not-assigned
            ParsedExpression("01.01n@01.02n").last_level_number

    def test_make_child_fails_on_bad_number(self):
        """
        ``make_child`` with a bad number should raise an exception.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^the number must be greater than 0$"):
            ParsedExpression("01.01n/01.02n").make_child('', -1, "n")

    def test_make_child_fails_on_bad_pos(self):
        """
        ``make_child`` with a bad pos should raise an exception.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^pos is not among valid choices$"):
            ParsedExpression("01.01n/01.02n").make_child('', 10, "invalid")

    def test_make_child_fails_specified(self):
        """
        ``make_child`` raises an exception when invoked on a specified
        expression.
        """
        with self.assertRaisesRegexp(
                ValueError,
                "^cannot make a child for a specified reference$"):
            ParsedExpression("01.01n@02.03n").make_child('', 2, "n")

    def test_make_child_branch_exists(self):
        """
        ``make_child`` produces a correct expression when the branch
        already exists.
        """
        child = ParsedExpression("01.01n/1.2n").make_child('', 2, "aj")
        self.assertEqual(unicode(child), "01.01n/1.2.2aj")

    def test_make_child_no_branch(self):
        """
        ``make_child`` produces a correct expression when the branch
        does not already exist.
        """
        child = ParsedExpression("01.01n").make_child('', 2, "aj")
        self.assertEqual(unicode(child), "01.01n/2aj")
