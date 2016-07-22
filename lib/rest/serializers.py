def noop(x):
    return x

# Adapted from:
# http://stackoverflow.com/a/31979444/1906307
class DynamicFieldsSerializerMixin(object):

    def __init__(self, *args, **kwargs):
        """
        This is a mixin that can be added to a Django REST Framework
        serializer to select a specific set of fields to
        serialize.

        The mixin computes a list of fields to be included in the
        serialization.  The list of fields passed to it can contain
        the following items:

        * An item starting with ``-`` indicates to remove this item
          from the list of included fields.

        * An item starting with ``=`` indicates to set the list of
          included fields to this item.

        * Otherwise, the item is added to the list of included fields.

        Once the optional ``-`` or ``=`` are removed, the item can
        either be a field name or a field set name. To indicate a
        field set name, it must begin with a ``@``. A field set is a
        predefined set of fields that the serializer class that uses
        this mixin may define. The ``@`` field set is special and
        indicates the "default" field set that will be included if
        ``fields`` is empty. An easy way to start from a blank list of
        fields is to start the list with ``-@``. Or the first item in
        the list could have an ``=`` before its name.

        Field sets are defined by setting a ``field_sets`` attribute
        on the class, which must have for value a dictionary that maps
        field set names to tuples of fields. The key ``""`` is the
        default field set. All computations of which fields to include
        implicitly start with the default field set. If a class that
        uses this mixin does not specify a default field set, the
        default is assumed to be the empty set.

        Note too that this mixin *removes* from the ``self.fields``
        object rather than *add* to it. This means that this mixin
        cannot add fields beyond the set of fields that the final
        serializer class is initialized with.

        Examples:

        * The list ``[]`` results in the default field set being used.

        * The list ``["-@"]`` would result in no fields being serialized.

        * The list ``["-@", "foo"]`` would result in only ``"foo"``
          being serialized.

        * The list ``["-foo"]`` would result in the serialization of
          the default field set with the exclusion of ``"foo"``.

        * The list ``["=foo"]`` would result in the serialization of
          ``foo`` and nothing else.

        * The list ``["@bar"]`` would result in the serialization of
          the default field set and those specified by the ``@bar``
          field set.

        * The list ``["=@bar"]`` would result in the serialization of
          the ``@bar`` field set.

        :params fields: The list of fields to add or remove.
        """
        self._selected_fields = kwargs.pop('fields', [])

        super(DynamicFieldsSerializerMixin, self).__init__(*args, **kwargs)

    def get_fields(self):
        super_fields = super(DynamicFieldsSerializerMixin, self).get_fields()
        field_sets = getattr(self, 'field_sets', {})
        default_field_set = frozenset(field_sets.get("", ()))

        # We implicitly start with the default set.
        include = default_field_set

        fields = self._selected_fields
        for field in fields:
            op = include.union

            if field.startswith("-"):
                field = field[1:]
                op = include.difference
            elif field.startswith("="):
                field = field[1:]
                op = noop

            if field.startswith("@"):
                field = field[1:]
                try:
                    fields = default_field_set if field == "" else \
                        frozenset(field_sets[field])
                except KeyError:
                    raise ValueError("unknown field set: " + field)
            else:
                fields = frozenset((field, ))

            include = op(fields)

        keys = frozenset(super_fields.keys())
        unknown = set(include) - keys
        if len(unknown):
            raise ValueError("unknown fields: " + ", ".join(unknown))

        return {k: super_fields[k] for k in include}
