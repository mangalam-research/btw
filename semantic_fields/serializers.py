from rest_framework import serializers
from django.db.models import Max, F

from .models import SemanticField, Lexeme
from lexicography.models import Entry, ChangeRecord
from lib.rest.serializers import DynamicFieldsSerializerMixin

class LexemeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lexeme
        fields = ("word", "fulldate")

class SemanticFieldSerializer(DynamicFieldsSerializerMixin,
                              serializers.HyperlinkedModelSerializer):

    class Meta:
        model = SemanticField
        fields = ("url", "path", "heading", "parent", "is_subcat",
                  "changerecords", "related_by_pos", "lexemes", "children",
                  "verbose_pos")

    field_sets = {
        # Define a default field set.
        "": ("url", "path", "heading", "is_subcat", "verbose_pos"),
        "search": ("parent", "related_by_pos"),
        "details": ("parent", "related_by_pos", "lexemes", "children")
    }

    url = serializers.SerializerMethodField()
    changerecords = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    related_by_pos = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    lexemes = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """
        This serializer accepts the following kwargs:

        * ``fields``: A list of fields to add or remove from the
          serialized data. The default set is ``"path", "heading",
          "parent"``. You may remove from this default by giving a
          name prefixed with ``"-"``. Or start from a clean slate with
          ``-@default``.

        * ``unpublished``: When ``False`` (the default) the serializer
        will include in ``changerecords`` only the latest published
        ``ChangeRecord`` associated with each lemma. When ``True``
        ``changerecords`` will contain all change records that were a hit,
        published **and** unpublished.
        """

        self.unpublished = kwargs.pop("unpublished", False)
        self.depths = kwargs.pop("depths", {})
        super(SemanticFieldSerializer, self).__init__(*args, **kwargs)

    def get_parent(self, sf):
        return self._generic_get_related(sf, "parent", False, None, True)

    def get_related_by_pos(self, sf):
        return self._generic_get_related(sf, "related_by_pos", True, 1)

    def get_children(self, sf):
        return self._generic_get_related(sf, "children", True)

    def _generic_get_related(self, sf, field_name, many, max_depth=None,
                             recurse=False):
        """
        A generic method for handling the serialization of related
        fields. The set of fields serialized on related fields is
        always the default set of fields defined on the serializer,
        plus possibly the actual field through which the relation is
        being serialized. The latter is included if ``recurse`` is
        ``True``.

        Care should be taken to prevent serializations that put a
        heavy load on the database. The rule that only the default set
        of fields is used in serialized related instance is part of
        this goal but users of this method should think about the
        impact of including related fields.

        :param sf: The record we are serializing.

        :param field_name: The name of the field we are serializing.

        :param many: Whether we are serializing one value or many.

        :param max_depth: For relations which are recursive, the
        maximum depth to serialize.

        :param recurse: Whether to include the field we are
        serializing in recursive relations.

        :returns: The serialized data.
        """
        field_value = getattr(sf, field_name)
        if many:
            if field_value is []:
                return []
        elif field_value is None:
            return None

        depth = self.depths.get(field_name, None)

        if depth is not None and max_depth:
            depth = min(max_depth, depth)
            # A negative value means: no bounds...
            if depth < 0:
                depth = max_depth

        if depth is None or depth == 0:
            field = serializers.HyperlinkedIdentityField(
                view_name='semantic_fields_semanticfield-detail',
                many=many)
            field.bind(field_name, self)
            return field.to_representation(field_value)

        next_depths = dict(self.depths)
        next_depths[field_name] = depth - 1 if depth > 0 else depth
        serializer = SemanticFieldSerializer(
            field_value,
            many=many,
            context=self.context,
            fields=[field_name] if recurse else [],
            unpublished=self.unpublished,
            depths=next_depths)
        return serializer.data

    def get_lexemes(self, sf):
        # We do this to work around
        # https://github.com/tomchristie/django-rest-framework/issues/3674
        #
        # When a release with PR
        # https://github.com/tomchristie/django-rest-framework/pull/3852
        # is released (3.4.2??), we can get rid of this.
        #
        return LexemeSerializer(sf.lexemes, many=True).data

    def get_url(self, sf):
        assert 'request' in self.context, (
            "`%s` requires the request in the serializer"
            " context. Add `context={'request': request}` when instantiating "
            "the serializer." % self.__class__.__name__
        )
        request = self.context["request"]
        return request.build_absolute_uri(sf.detail_url)

    def get_changerecords(self, sf):
        crs = ChangeRecord.objects.with_semantic_field(
            sf.path, self.unpublished)

        if not self.unpublished:
            # When we do not include the unpublished records we want
            # only those changerecords that are the latest ones of
            # each article they belong to. e.g. if article for lemma X
            # has two changerecords published A and B, and B is later
            # than A, we want only B.

            #
            # `distinct` is dependent on PostgreSQL, but we are
            # already dependent elsewhere.
            #
            crs = crs.order_by('entry', '-datetime').distinct('entry')

            # The platform-independent way would be:
            #
            # crs = crs \
            #     .annotate(latest_pub_date=Max(
            #         'entry__latest_published__datetime')) \
            #     .filter(datetime=F('latest_pub_date'))

        return [{
            "lemma": x.lemma,
            "url": x.get_absolute_url(),
            "datetime": x.datetime,
            "published": x.published,
        } for x in crs]
