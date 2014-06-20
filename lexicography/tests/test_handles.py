import os

from django.test import TransactionTestCase
from django.db import transaction

from .. import handles
from ..models import Handle


dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json", ))


class HandleManagerTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.a = handles.HandleManager("a")
        self.b = handles.HandleManager("b")

    def test_make_unassociated_returns_unique_values(self):
        self.assertEqual(self.a.make_unassociated(), 0, "first")
        self.assertEqual(self.a.make_unassociated(), 1, "second")

    def test_make_unassociated_is_per_session(self):
        self.assertEqual(self.a.make_unassociated(), 0, "first")
        self.assertEqual(self.a.make_unassociated(), 1, "second")

        self.assertEqual(self.b.make_unassociated(), 0, "first")
        self.assertEqual(self.b.make_unassociated(), 1, "second")

    def test_associate_associates(self):
        handle = self.a.make_unassociated()
        self.a.associate(handle, 1)
        self.assertEqual(self.a.id(handle), 1)

    def test_associate_is_per_session(self):
        handle_a = self.a.make_unassociated()
        handle_b = self.b.make_unassociated()
        self.assertEqual(handle_a, handle_b)

        self.a.associate(handle_a, 1)
        self.assertEqual(self.a.id(handle_a), 1)
        self.assertIsNone(self.b.id(handle_b))

    def test_id_works_with_unassociated_handle(self):
        handle1 = self.a.make_unassociated()
        self.assertIsNone(self.a.id(handle1))

    def test_id_fails_on_unknown_handle(self):
        self.assertRaisesRegexp(
            ValueError,
            "handle 0 does not exist",
            self.a.id, 0)

    def test_make_unassociated_remembers(self):
        self.assertEqual(self.a.make_unassociated(), 0, "first")
        self.assertEqual(self.a.make_unassociated(), 1, "second")

        # This creates an object which will have to read from the DB.
        new_a = handles.HandleManager("a")

        self.assertEqual(new_a.make_unassociated(), 2, "third")

    def test_associate_remembers(self):
        handle_0 = self.a.make_unassociated()
        handle_1 = self.a.make_unassociated()

        self.assertIsNone(self.a.id(handle_0))
        self.assertIsNone(self.a.id(handle_1))

        self.a.associate(handle_0, 1)

        # This creates an object which will have to read from the DB
        # to recall what was associated
        new_a = handles.HandleManager("a")

        self.assertEqual(new_a.id(handle_0), 1)
        self.assertIsNone(new_a.id(handle_1))

    def test_associate_is_affected_by_rollbacks(self):
        transaction.set_autocommit(False)
        try:
            handle_0 = self.a.make_unassociated()
            transaction.commit()
            self.a.associate(handle_0, 1)
            transaction.rollback()

            self.assertIsNone(Handle.objects.get(handle=handle_0).entry,
                              "no entry should be associated in the database")
            self.assertIsNone(self.a.id(handle_0),
                              "the manager should not return an id")
        finally:
            transaction.rollback()
            transaction.set_autocommit(True)

    def test_make_unassociated_is_affected_by_rollbacks(self):
        transaction.set_autocommit(False)
        try:
            handle_0 = self.a.make_unassociated()
            transaction.rollback()

            self.assertEqual(Handle.objects.filter(handle=handle_0).count(),
                             0,
                             "no entry should be associated in the database")
            self.assertRaisesRegexp(ValueError,
                                    "handle 0 does not exist",
                                    self.a.associate, handle_0, 1)

        finally:
            transaction.rollback()
            transaction.set_autocommit(True)
