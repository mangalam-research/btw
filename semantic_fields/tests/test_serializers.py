import mock

from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from ..models import SemanticField
from ..serializers import SemanticFieldSerializer
from .util import MinimalQuery, FakeChangeRecord

def make_context(request):
    return {"request": request}

def _make_test_url(sf):
    return "http://testserver" + sf.detail_url

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class SerializerTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cat1 = cls.cat1 = SemanticField(path="01n", heading="term")
        cat1.save()

        cat2 = cls.cat2 = SemanticField(path="02n", heading="aaaa", catid="1")
        cat2.save()

        cat3 = cls.cat3 = SemanticField(path="01.01n", heading="bwip",
                                        parent=cat1)
        cat3.save()

        cat4 = cls.cat4 = SemanticField(path="01.01|01v", heading="qqq",
                                        parent=cat3)
        cat4.save()

        custom = cls.custom = SemanticField.objects.make_field("custom", "n")

        custom.make_related_by_pos("verb", "v")
        custom.make_related_by_pos("adjective", "aj")

        cls.request_factory = RequestFactory()
        cls.request = cls.request_factory.get("/foo")
        cls.context = make_context(cls.request)

    def test_default(self):
        """
        A serializer serializes the default set of fields.
        """
        data = SemanticFieldSerializer(self.cat1, context=self.context).data
        self.assertEqual(data, {
            "url": _make_test_url(self.cat1),
            "path": "01n",
            "heading": "term",
            "is_subcat": False,
            "verbose_pos": "Noun",
        })

        data = SemanticFieldSerializer(self.cat2, context=self.context).data
        self.assertEqual(data, {
            "url": _make_test_url(self.cat2),
            "path": "02n",
            "heading": "aaaa",
            "is_subcat": False,
            "verbose_pos": "Noun",
        })

        data = SemanticFieldSerializer(self.cat3, context=self.context).data
        self.assertEqual(data, {
            "url": _make_test_url(self.cat3),
            "path": "01.01n",
            "heading": "bwip",
            "is_subcat": False,
            "verbose_pos": "Noun",
        })

    def test_search_field_set(self):
        """
        A serializer serializes the search field set.
        """
        fields = ["@search"]

        def make_data(cat):
            return SemanticFieldSerializer(cat, context=self.context,
                                           fields=fields).data
        data = make_data(self.cat1)
        self.assertEqual(data, {
            "url": _make_test_url(self.cat1),
            "path": "01n",
            "heading": "term",
            "parent": None,
            "is_subcat": False,
            "verbose_pos": "Noun",
            "related_by_pos": [],
        })

        data = make_data(self.cat2)
        self.assertEqual(data, {
            "url": _make_test_url(self.cat2),
            "path": "02n",
            "heading": "aaaa",
            "parent": None,
            "is_subcat": False,
            "verbose_pos": "Noun",
            "related_by_pos": [],
        })

        data = make_data(self.cat3)
        self.assertEqual(data, {
            "url": _make_test_url(self.cat3),
            "path": "01.01n",
            "heading": "bwip",
            "parent": _make_test_url(self.cat1),
            "is_subcat": False,
            "verbose_pos": "Noun",
            "related_by_pos": [],
        })

    def test_wide_published(self):
        """
        A serializer set to produce changerecords and covers only
        published entries.
        """
        with mock.patch("semantic_fields.serializers.ChangeRecord"
                        ".objects.with_semantic_field") as mocked:
            fake_crs = [{"lemma": "foo", "url": "/lexicography/foo",
                         "datetime": "2000-01-01", "published": True}]
            mocked.return_value = MinimalQuery([FakeChangeRecord(**kwargs)
                                                for kwargs in fake_crs])

            data = SemanticFieldSerializer(self.cat1,
                                           context=self.context,
                                           fields=["changerecords"]).data
            self.assertEqual(data, {
                "url": _make_test_url(self.cat1),
                "path": "01n",
                "heading": "term",
                "is_subcat": False,
                "verbose_pos": "Noun",
                "changerecords": fake_crs,
            })
            mocked.assert_called_with("01n", False)

    def test_wide_unpublished(self):
        """
        A serializer set to produce changerecords and covers unpublished
        records produces correct data.
        """
        with mock.patch("semantic_fields.serializers.ChangeRecord"
                        ".objects.with_semantic_field") as mocked:
            fake_crs = [{"lemma": "foo", "url": "/lexicography/foo",
                         "datetime": "2000-01-01", "published": False}]
            mocked.return_value = MinimalQuery([FakeChangeRecord(**kwargs) for
                                                kwargs in fake_crs])

            data = SemanticFieldSerializer(self.cat1, fields=["changerecords"],
                                           context=self.context,
                                           unpublished=True).data
            self.assertEqual(data, {
                "url": _make_test_url(self.cat1),
                "path": "01n",
                "heading": "term",
                "is_subcat": False,
                "verbose_pos": "Noun",
                "changerecords": fake_crs,
            })
            mocked.assert_called_with("01n", True)

    def test_parents_unbound(self):
        """
        A serializer set to have an unbound parent recursion returns the
        right data.
        """
        data = SemanticFieldSerializer(self.cat4, context=self.context,
                                       fields=["@search", "-related_by_pos"],
                                       depths={"parent": -1},
                                       unpublished=True).data
        self.assertEqual(data, {
            "url": _make_test_url(self.cat4),
            "path": "01.01|01v",
            "heading": "qqq",
            "parent": {
                "url": _make_test_url(self.cat3),
                "path": "01.01n",
                "heading": "bwip",
                "parent": {
                    "url": _make_test_url(self.cat1),
                    "path": "01n",
                    "heading": "term",
                    "parent": None,
                    "is_subcat": False,
                    "verbose_pos": "Noun",
                },
                "is_subcat": False,
                "verbose_pos": "Noun",
            },
            "is_subcat": True,
            "verbose_pos": "Verb",
        })

    def test_related_by_pos_no_depth(self):
        """
        A serializer set to have related_by_pos returns the right data.
        """
        data = SemanticFieldSerializer(self.custom, context=self.context,
                                       fields=["@search", "-parent"]).data
        self.assertEqual(data, {
            "url": _make_test_url(self.custom),
            "path": self.custom.path,
            "heading": "custom",
            "is_subcat": False,
            "verbose_pos": "Noun",
            "related_by_pos":
            [_make_test_url(r) for r in self.custom.related_by_pos]
        })

    def test_related_by_pos_unbound(self):
        """
        A serializer set to have an unbound related_by_pos recursion
        returns the right data.
        """
        data = SemanticFieldSerializer(self.custom, context=self.context,
                                       fields=["@search", "-parent"],
                                       depths={"related_by_pos": -1}).data
        self.assertEqual(data, {
            "url": _make_test_url(self.custom),
            "path": self.custom.path,
            "heading": "custom",
            "is_subcat": False,
            "verbose_pos": "Noun",
            "related_by_pos": [
                SemanticFieldSerializer(r, context=self.context,
                                        fields=[]).data
                for r in self.custom.related_by_pos
            ]
        })
