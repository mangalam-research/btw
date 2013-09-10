from django.utils import unittest

from .. import handles

class HandleManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.manager = handles.HandleManager("q")

    def test_next_name(self):
        # pylint: disable-msg=W0212
        self.assertEqual(self.manager._next_name, "q.0")
        self.assertEqual(self.manager._next_name, "q.1")

    def test_make_associated(self):
        self.assertEqual(self.manager.make_associated(1), "q.0")

    def test_make_associated_returns_constant_values(self):
        self.assertEqual(self.manager.make_associated(1),
                         self.manager.make_associated(1))
        self.assertEqual(self.manager.make_associated(2),
                         self.manager.make_associated(2))

    def test_make_associated_returns_diff_values_for_diff_ids(self):
        self.assertNotEqual(self.manager.make_associated(1),
                            self.manager.make_associated(2))

    def test_make_unassociated_returns_unique_values(self):
        self.assertNotEqual(self.manager.make_unassociated(),
                            self.manager.make_unassociated())

    def test_associate_associates(self):
        handle = self.manager.make_unassociated()
        self.manager.associate(handle, 1)
        self.assertEqual(self.manager.make_associated(1), handle)

    def test_associate_fails_on_already_associated_handle(self):
        handle1 = self.manager.make_associated(1)
        self.assertRaisesRegexp(ValueError,
                                "handle q.0 already associated",
                                self.manager.associate, handle1, 1)

    def test_associate_fails_on_already_associated_id(self):
        self.manager.make_associated(1)
        handle2 = self.manager.make_unassociated()
        self.assertRaisesRegexp(ValueError,
                                "id 1 already associated",
                                self.manager.associate, handle2, 1)


    def test_id_works_with_associated_handle(self):
        handle1 = self.manager.make_associated(1)
        self.assertEqual(self.manager.id(handle1), 1)
        handle2 = self.manager.make_associated(2)
        self.assertEqual(self.manager.id(handle2), 2)

    def test_id_works_with_unassociated_handle(self):
        handle1 = self.manager.make_unassociated()
        self.assertIsNone(self.manager.id(handle1))
