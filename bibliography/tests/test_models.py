from unittest import TestCase
import mock
import json
import datetime

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_is_not_none, \
    assert_not_equal, assert_raises, assert_not_regexp_matches, \
    assert_regexp_matches
from django.core.exceptions import ValidationError

from ..models import Item, PrimarySource
from .. import models
from . import mock_zotero


mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Name 1 for Title 1"},
                {"firstName": "FirstName 2 for Title 1",
                 "lastName": "LastName 2 for Title 1"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "2",
            "title": "Title 2",
            "date": "Date 2",
            "creators": [
                {"name": "Name 1 for Title 2"},
                {"firstName": "FirstName 2 for Title 2",
                 "lastName": "LastName 2 for Title 2"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    }
])

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: (mock_records.values, {}))
get_item_mock = mock.Mock(side_effect=mock_records.get_item)


@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
class ItemTestCase(TestCase):

    def setUp(self):
        mock_records.reset()

    def alter_record(self, record):
        data = record["data"]
        for key in ("title", "date"):
            data[key] += " (bis)"

        data["creators"][0]["name"] += " (bis)"

    def test_create(self):
        """
        Test that we can create an item.
        """
        Item(item_key="1", uid=Item.objects.zotero.full_uid)

    def test_values(self):
        """
        Test that the values of the fields are generally correct.
        """
        item = Item(item_key="1", uid=Item.objects.zotero.full_uid)
        assert_equal(item.title, "Title 1")
        assert_equal(item.date, "Date 1")
        assert_equal(item.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")
        assert_equal(item.item, json.dumps(mock_records.get_item("1")))
        assert_equal(item.uid, Item.objects.zotero.full_uid)
        # pylint: disable=protected-access
        assert_equal(item._item, mock_records.get_item("1"))
        assert_is_not_none(item.freshness)

    def test_refresh(self):
        """
        Test that a stale item is automatically refreshed.
        """
        item = Item(item_key="1", uid=Item.objects.zotero.full_uid)

        assert_equal(item.title, "Title 1")
        assert_equal(item.date, "Date 1")
        assert_equal(item.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")

        self.alter_record(mock_records.values[0])

        # This forces refreshing. We don't use mark_stale so that we
        # can test the time computation.
        item.freshness -= models.MINIMUM_FRESHNESS + \
            datetime.timedelta(seconds=1)
        item.save()

        item2 = Item.objects.get(id=item.id)

        assert_equal(item2.title, "Title 1 (bis)")
        assert_equal(item2.date, "Date 1 (bis)")
        assert_equal(item2.creators,
                     "Name 1 for Title 1 (bis), LastName 2 for Title 1")

        assert_not_equal(item.freshness, item2.freshness)

    def test_fresh(self):
        """
        Test that a fresh item is not refreshed.
        """
        item = Item(item_key="1", uid=Item.objects.zotero.full_uid)

        assert_equal(item.title, "Title 1")
        assert_equal(item.date, "Date 1")
        assert_equal(item.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")

        self.alter_record(mock_records.values[0])

        # This item should be the same as the first.
        item2 = Item.objects.get(id=item.id)

        assert_equal(item2.title, "Title 1")
        assert_equal(item2.date, "Date 1")
        assert_equal(item2.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")

        assert_equal(item.freshness, item2.freshness)

    def test_mark_stale(self):
        """
        Test that mark_stale causes a refresh.
        """
        item = Item(item_key="1", uid=Item.objects.zotero.full_uid)

        assert_equal(item.title, "Title 1")
        assert_equal(item.date, "Date 1")
        assert_equal(item.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")

        self.alter_record(mock_records.values[0])

        item.mark_stale()

        item2 = Item.objects.get(id=item.id)

        assert_equal(item2.title, "Title 1 (bis)")
        assert_equal(item2.date, "Date 1 (bis)")
        assert_equal(item2.creators,
                     "Name 1 for Title 1 (bis), LastName 2 for Title 1")

        assert_not_equal(item.freshness, item2.freshness)

    def test_mark_all_stale(self):
        """
        Test that mark_all_stale causes refreshing all records.
        """
        items = Item.objects.all()

        for item in items:
            assert_not_regexp_matches(item.title, ur" \(bis\)$")

        for record in mock_records.values:
            self.alter_record(record)

        Item.objects.mark_all_stale()

        items2 = Item.objects.all()

        for item in items2:
            assert_regexp_matches(item.title, ur" \(bis\)$")

class PrimarySourceTestCase(TestCase):

    def setUp(self):
        mock_records.reset()
        self.patch = mock.patch.multiple(
            "bibliography.zotero.Zotero", get_all=get_all_mock,
            get_item=get_item_mock)
        self.patch.start()
        self.item = Item(item_key="1", uid=Item.objects.zotero.full_uid)

    def tearDown(self):
        self.patch.stop()

    def test_create(self):
        """Test that we can create a source without getting an error."""
        source = PrimarySource(item=self.item, reference_title="Foo",
                               genre="SU")
        source.save()

    def test_reference_title_mandatory(self):
        """Test that we cannot create a source with a blank reference_title."""
        source = PrimarySource(item=self.item, genre="SU")

        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     "{'reference_title': [u'This field cannot be null.']}")

    def test_reference_title_cannot_be_empty(self):
        """
        Test that we cannot create a source with a reference_title which is
        an empty string.
        """
        source = PrimarySource(
            item=self.item, reference_title="   ", genre="SU")

        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     "{'reference_title': "
                     "[u'This field cannot contain only spaces.']}")

    def test_genre_mandatory(self):
        """Test that we cannot create a source without a genre."""
        source = PrimarySource(item=self.item, reference_title="Foo2")
        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     "{'genre': [u'This field cannot be null.']}")

    def test_genre_cannot_be_empty(self):
        """
        Test that we cannot create a source with a genre which is an
        empty value.
        """
        source = PrimarySource(
            item=self.item, reference_title="Foo2", genre="")
        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     "{'genre': [u'This field cannot be blank.']}")

    def test_genre_needs_correct_value(self):
        """
        Test that we cannot create a source with a genre which is an
        invalid value.
        """
        source = PrimarySource(
            item=self.item, reference_title="Foo2", genre="XX")
        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     '{\'genre\': [u"Value \'XX\' is not a valid choice."]}')

    def test_no_duplicate_titles(self):
        """
        Test that we cannot create a source with a genre which is an
        invalid value.
        """
        PrimarySource(
            item=self.item, reference_title="Blah", genre="SU").save()
        source = PrimarySource(
            item=self.item, reference_title=" Blah ", genre="SU")
        with assert_raises(ValidationError) as cm:
            source.save()
        assert_equal(str(cm.exception),
                     "{'reference_title': "
                     "[u'Primary source with this Reference title already "
                     "exists.']}")
