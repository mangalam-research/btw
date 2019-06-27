from unittest import TestCase

from lib.settings import Settings

class SettingsTest(TestCase):

    def test_set_get(self):
        "Sets and gets values."
        x = Settings()
        x.a = 1
        x.b = 2
        self.assertEqual(x.a, 1)
        self.assertEqual(x.b, 2)

    def test_cannot_set_parent_or_attrs(self):
        "Cannot set the attributes 'parent' or 'attrs'."
        x = Settings()
        with self.assertRaisesRegex(AttributeError,
                                    "'parent' is a reserved name"):
            x.parent = 1
        with self.assertRaisesRegex(AttributeError,
                                    "'attrs' is a reserved name"):
            x.attrs = 1

    def test_parent(self):
        "Fetches values from parent."
        parent = Settings()
        child = Settings(parent)
        parent.a = 1
        parent.b = 2
        child.b = "overriden"
        self.assertEqual(child.a, 1)
        self.assertEqual(child.b, "overriden")

    def test_no_callable_overwrite_non_callable(self):
        "Disallows overwriting a callable with non-callable."
        x = Settings()
        x.a = lambda s: 1
        with self.assertRaisesRegex(AttributeError,
                                    "^trying to override attribute 'a' "
                                    "from a callable value to a non-callable "
                                    "one"):
            x.a = 1

    def test_callable_overwrite_with_callable(self):
        "Allows overwriting a callable with a callable."
        x = Settings()
        x.a = lambda s: s.init + " original"
        x.a = lambda s: s.a + " and derived"
        x.init = "init"
        self.assertEqual(x.a, "init original and derived")

    def test_as_dict(self):
        "The ``as_dict`` method returns a dictionary of values."
        x = Settings()
        x.a = lambda s: s.init + " original"
        x.a = lambda s: s.a + " and derived"
        x.init = "init"
        self.assertEqual(x.as_dict(), {
            "a": "init original and derived",
            "init": "init",
        })
