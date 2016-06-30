from rest_framework import serializers
from django.db.models import Max, F

from .models import SemanticField
from lexicography.models import Entry, ChangeRecord

class SemanticFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = SemanticField
        fields = ("path", "heading", "parent", "hte_url", "changerecords")

    DEFAULT_SCOPE = "default"
    WIDE_SCOPE = "wide"

    changerecords = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """
        This serializer accepts the following kwargs:

        * ``scope``: When set to
        ``SemanticFieldSerializer.DEFAULT_SCOPE`` (the default) there
        won't be an ``changerecords`` field in the serialized data. When set
        to ``SemanticFieldSerializer.WIDE_SCOPE`` ``changerecords`` will be
        generated.

        * ``unpublished``: When ``False`` (the default) the serializer
        will include in ``changerecords`` only the latest published
        ``ChangeRecord`` associated with each lemma. When ``True``
        ``changerecords`` will contain all change records that were a hit,
        published **and** unpublished.
        """
        scope = kwargs.pop("scope", None)
        self.unpublished = kwargs.pop("unpublished", False)
        super(SemanticFieldSerializer, self).__init__(*args, **kwargs)

        # ``changerecords`` must be included by default to avoid an error from
        # ModelSerializer. If we don't need it, then we pop it.
        if scope != self.WIDE_SCOPE:
            self.fields.pop("changerecords")

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
