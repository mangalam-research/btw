from unittest import mock

from django.test import TestCase
# pylint: disable=no-name-in-module
from nose.tools import assert_true, assert_equal

from ..forms import PrimarySourceForm
from ..models import Item, PrimarySource
from .. import tasks
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
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

class PrimarySourceFormTestCase(TestCase):

    def setUp(self):
        mock_records.reset()
        self.patch = mock.patch.multiple(
            "bibliography.zotero.Zotero", get_all=get_all_mock,
            get_item=get_item_mock)
        self.patch.start()
        tasks.fetch_items()

        self.item = Item.objects.get(item_key="1")

    def tearDown(self):
        self.patch.stop()

    def test_valid_form(self):
        """A form with valid data is recognized as valid."""
        data = {
            'item': self.item.pk,
            'reference_title': 'Foo',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_true(form.is_valid())

    def test_empty_reference_title(self):
        """An empty reference title is invalid."""
        data = {
            'item': self.item.pk,
            'reference_title': '',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'reference_title': ['This field is required.']})

    def test_blank_reference_title(self):
        """A reference_title with only spaces is not valid."""
        data = {
            'item': self.item.pk,
            'reference_title': '   ',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'reference_title':
                      ['This field cannot contain only spaces.']})

    def test_blank_genre(self):
        """Genre must be filled."""
        data = {
            'item': self.item.pk,
            'reference_title': 'Foo',
            'genre': ''
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors, {'genre': ['This field is required.']})

    def test_invalid_genre(self):
        """A genre which is not a valid choice is disallowed."""
        data = {
            'item': self.item.pk,
            'reference_title': 'Foo',
            'genre': 'XX'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'genre': ['Select a valid choice. XX is not one of '
                                'the available choices.']})

    def test_item_must_be_filled(self):
        """The item field must refer to a record."""
        data = {
            'item': None,
            'reference_title': 'Foo',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'item': ['This field is required.']})

    def test_item_must_be_real(self):
        """The item field must refer to an existing record."""
        data = {
            'item': 9999,
            'reference_title': 'Foo',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'item': ['Select a valid choice. That choice is not '
                               'one of the available choices.']})

    def test_no_duplicate_reference_titles(self):
        """A duplicate reference title is invalid."""
        PrimarySource(item=self.item, reference_title="Foo",
                      genre="SU").save()
        data = {
            'item': self.item.pk,
            'reference_title': 'Foo',
            'genre': 'SU'
        }
        form = PrimarySourceForm(data)
        assert_equal(form.errors,
                     {'reference_title': ['Primary source with this '
                                          'Reference title already exists.']})
