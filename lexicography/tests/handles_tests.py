import os

from django.test import TransactionTestCase
from django.db import transaction

from .. import handles
from ..models import Entry


dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("views.json", ))

class HandleManagerTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.a = handles.HandleManager("a")
        self.b = handles.HandleManager("b")

    def test_make_unassociated_returns_unique_values(self):
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 0, "first")
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 1, "second")

    def test_make_unassociated_is_per_session(self):
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 0, "first")
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 1, "second")

        with transaction.commit_on_success():
            self.assertEqual(self.b.make_unassociated(), 0, "first")
        with transaction.commit_on_success():
            self.assertEqual(self.b.make_unassociated(), 1, "second")

    def test_associate_associates(self):
        with transaction.commit_on_success():
            handle = self.a.make_unassociated()
        with transaction.commit_on_success():
            self.a.associate(handle, 1)
        with transaction.commit_on_success():
            self.assertEqual(self.a.id(handle), 1)

    def test_associate_is_per_session(self):
        with transaction.commit_on_success():
            handle_a = self.a.make_unassociated()
            handle_b = self.b.make_unassociated()
        self.assertEqual(handle_a, handle_b)

        with transaction.commit_on_success():
            self.a.associate(handle_a, 1)
        with transaction.commit_on_success():
            self.assertEqual(self.a.id(handle_a), 1)
            self.assertIsNone(self.b.id(handle_b))

    def test_id_works_with_unassociated_handle(self):
        with transaction.commit_on_success():
            handle1 = self.a.make_unassociated()
        with transaction.commit_on_success():
            self.assertIsNone(self.a.id(handle1))

    def test_id_fails_on_unknown_handle(self):
        with transaction.commit_on_success():
            self.assertRaisesRegexp(
                ValueError,
                "handle 0 does not exist",
                self.a.id, 0)

    def test_make_unassociated_remembers(self):
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 0, "first")
        with transaction.commit_on_success():
            self.assertEqual(self.a.make_unassociated(), 1, "second")

        # This creates an object which will have to read from the DB.
        new_a = handles.HandleManager("a")

        with transaction.commit_on_success():
            self.assertEqual(new_a.make_unassociated(), 2, "third")

    def test_associate_remembers(self):
        with transaction.commit_on_success():
            handle_0 = self.a.make_unassociated()
            handle_1 = self.a.make_unassociated()

        with transaction.commit_on_success():
            self.assertIsNone(self.a.id(handle_0))
            self.assertIsNone(self.a.id(handle_1))

        with transaction.commit_on_success():
            self.a.associate(handle_0, Entry.objects.get(id=1))

        # This creates an object which will have to read from the DB
        # to recall what was associated
        new_a = handles.HandleManager("a")

        with transaction.commit_on_success():
            self.assertEqual(new_a.id(handle_0), 1)
            self.assertIsNone(new_a.id(handle_1))
