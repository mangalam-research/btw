from bibliography.tests import mock_zotero
from unittest import mock

#
# What we have here is the patch to the Zotero code required so that
# Django does not got talking to the Zotero server. It is needed both
# in the live server **and** in the workers started for the live
# server so we keep it here.
#

mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Abelard (Name 1 for Title 1)"},
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
                {"name": "Beth (Name 1 for Title 2)"},
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
    },
    {
        "data":
        {
            "key": "3",
            "title": "Title 3",
            "date": "Date 3",
            "creators": [
                {"name": "Zeno (Name 1 for Title 3)"},
                {"firstName": "FirstName 2 for Title 3",
                 "lastName": "LastName 2 for Title 3"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo3.com",
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

patch = mock.patch.multiple("bibliography.zotero.Zotero",
                            get_all=get_all_mock,
                            get_item=get_item_mock)
