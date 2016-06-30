import mock

from django.test import TestCase

from ..models import SemanticField
from ..serializers import SemanticFieldSerializer
from .util import MinimalQuery, FakeChangeRecord

class ViewsTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cat1 = cls.cat1 = SemanticField(path="01n", heading="term")
        cat1.save()

        cat2 = cls.cat2 = SemanticField(path="02n", heading="aaaa", catid="1")
        cat2.save()

        cat3 = cls.cat3 = SemanticField(path="01.01n", heading="bwip",
                                        parent=cat1)
        cat3.save()

    def test_narrow(self):
        """
        A serializer set to produce a narrow set of field (the default)
        produces correct data.
        """
        data = SemanticFieldSerializer(self.cat1).data
        self.assertEqual(data, {
            "path": "01n",
            "heading": "term",
            "parent": None,
            "hte_url": None,
        })

        data = SemanticFieldSerializer(self.cat2).data
        self.assertEqual(data, {
            "path": "02n",
            "heading": "aaaa",
            "parent": None,
            "hte_url":
            "http://historicalthesaurus.arts.gla.ac.uk/category/?id=1",
        })

        data = SemanticFieldSerializer(self.cat3).data
        self.assertEqual(data, {
            "path": "01.01n",
            "heading": "bwip",
            "parent": self.cat1.id,
            "hte_url": None,
        })

    def test_wide_published(self):
        """
        A serializer set to produce a wide set of fields and covers only
        published entries.
        """
        with mock.patch("semantic_fields.serializers.ChangeRecord"
                        ".objects.with_semantic_field") as mocked:
            fake_crs = [{"lemma": "foo", "url": "/lexicography/foo",
                         "datetime": "2000-01-01", "published": True}]
            mocked.return_value = MinimalQuery([FakeChangeRecord(**kwargs)
                                                for kwargs in fake_crs])

            data = SemanticFieldSerializer(self.cat1, scope="wide").data
            self.assertEqual(data, {
                "path": "01n",
                "heading": "term",
                "parent": None,
                "hte_url": None,
                "changerecords": fake_crs
            })
            mocked.assert_called_with("01n", False)

    def test_wide_unpublished(self):
        """
        A serializer set to produce a narrow set of field (the default)
        produces correct data.
        """
        with mock.patch("semantic_fields.serializers.ChangeRecord"
                        ".objects.with_semantic_field") as mocked:
            fake_crs = [{"lemma": "foo", "url": "/lexicography/foo",
                         "datetime": "2000-01-01", "published": False}]
            mocked.return_value = MinimalQuery([FakeChangeRecord(**kwargs) for
                                                kwargs in fake_crs])

            data = SemanticFieldSerializer(self.cat1, scope="wide",
                                           unpublished=True).data
            self.assertEqual(data, {
                "path": "01n",
                "heading": "term",
                "parent": None,
                "hte_url": None,
                "changerecords": fake_crs
            })
            mocked.assert_called_with("01n", True)
