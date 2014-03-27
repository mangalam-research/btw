from unittest import TestCase
import mock
import json
import datetime

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_is_none, assert_is_not_none, \
    assert_not_equal

from ..models import Item
from .. import models
from . import mock_zotero


mock_records = mock_zotero.Records([
    {
        "itemKey": "1",
        "title": "Title 1",
        "date": "Date 1",
        "creators": [
            {"name": "Name 1 for Title 1"},
            {"firstName": "FirstName 2 for Title 1",
             "lastName": "LastName 2 for Title 1"},
        ]
    },
    {
        "itemKey": "2",
        "title": "Title 2",
        "date": "Date 2",
        "creators": [
            {"name": "Name 1 for Title 2"},
            {"firstName": "FirstName 2 for Title 2",
             "lastName": "LastName 2 for Title 2"},
        ]
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
        assert_is_none(item.reference_title)
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

        for key in ("title", "date"):
            mock_records.values[0][key] += " (bis)"

        mock_records.values[0]["creators"][0]["name"] += " (bis)"

        # This forces refreshing.
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

        # We are modifying the fake Zotero database.
        for key in ("title", "date"):
            mock_records.values[0][key] += " (bis)"

        mock_records.values[0]["creators"][0]["name"] += " (bis)"

        # This item should be the same as the first.
        item2 = Item.objects.get(id=item.id)

        assert_equal(item2.title, "Title 1")
        assert_equal(item2.date, "Date 1")
        assert_equal(item2.creators,
                     "Name 1 for Title 1, LastName 2 for Title 1")

        assert_equal(item.freshness, item2.freshness)
