

from unittest import TestCase

from rest_framework import serializers

from lib.rest.serializers import DynamicFieldsSerializerMixin

class Something(object):

    def __init__(self, foo="", bar="", baz=""):
        self.foo = foo
        self.bar = bar
        self.baz = baz
        self.q = "qval"


class SerializerWithoutFieldSet(DynamicFieldsSerializerMixin,
                                serializers.Serializer):

    foo = serializers.CharField()
    bar = serializers.CharField()
    baz = serializers.CharField()


class SerializerWithFieldSets(SerializerWithoutFieldSet):

    field_sets = {
        "": ("foo", "bar"),
        "special": ("bar", "baz"),
    }

class SerializerWithBadFieldSets(SerializerWithoutFieldSet):

    field_sets = {
        "": ("foo", "bar", "bleh"),
    }


class DynamicFieldsSerializerTestCase(TestCase):

    instance = Something(foo="fooval", bar="barval", baz="bazval")

    def assertSerialized(self, serializer, fields):
        expected = {field: getattr(self.instance, field) for field in fields}
        self.assertEqual(serializer.data, expected)

    def test_no_field_set_no_fields(self):
        """
        A serializer with no ``field_set`` defined and no fields
        specified, serializes nothing.
        """
        s = SerializerWithoutFieldSet(self.instance)
        self.assertSerialized(s, [])

    def test_no_field_set_fields(self):
        """
        A serializer with no ``field_set`` defined and fields
        specified, serializes the fields specified.
        """
        s = SerializerWithoutFieldSet(self.instance, fields=["foo", "bar"])
        self.assertSerialized(s, ["foo", "bar"])

    def test_default_field_set(self):
        """
        A serializer with no a default field set defined and no fields
        specified, serializes the default field set
        """
        s = SerializerWithFieldSets(self.instance)
        self.assertSerialized(s, ["foo", "bar"])

    def test_remove_default_field_set(self):
        """
        ``["-@"]`` serializes nothing.
        """
        s = SerializerWithFieldSets(self.instance, fields=["-@"])
        self.assertSerialized(s, [])

    def test_annul_default(self):
        """
        ``["-@", "foo"]`` serializes only ``foo``.
        """
        s = SerializerWithFieldSets(self.instance, fields=["-@", "foo"])
        self.assertSerialized(s, ["foo"])

    def test_remove_from_default(self):
        """
        ``["-foo"]`` serializes only the default without ``foo``.
        """
        s = SerializerWithFieldSets(self.instance, fields=["-foo"])
        self.assertSerialized(s, ["bar"])

    def test_equal_sets_field(self):
        """
        ``["=foo"]`` serializes only ``foo``.
        """
        s = SerializerWithFieldSets(self.instance, fields=["=foo"])
        self.assertSerialized(s, ["foo"])

    def test_special_field_set(self):
        """
        ``["@.."]`` combines the specified field set with the default.
        """
        s = SerializerWithFieldSets(self.instance, fields=["@special"])
        self.assertSerialized(s, ["foo", "bar", "baz"])

    def test_equal_field_set(self):
        """
        ``["=@.."]`` sets the included fields to the specified field set.
        """
        s = SerializerWithFieldSets(self.instance, fields=["=@special"])
        self.assertSerialized(s, ["bar", "baz"])

    def test_unknown_field(self):
        """
        Fails if an unknown field is passed.
        """
        with self.assertRaisesRegex(ValueError, "unknown fields: q"):
            s = SerializerWithFieldSets(self.instance, fields=["q"])
            s.get_fields()

    def test_unknown_query_set(self):
        """
        Fails if an unknown query set is passed.
        """
        with self.assertRaisesRegex(ValueError, "unknown field set: q"):
            s = SerializerWithFieldSets(self.instance, fields=["@q"])
            s.get_fields()

    def test_unknown_field_in_field_set(self):
        """
        Fails if a used field set refers to an unknown field.
        """
        with self.assertRaisesRegex(ValueError, "unknown fields: bleh"):
            s = SerializerWithBadFieldSets(self.instance)
            s.get_fields()
