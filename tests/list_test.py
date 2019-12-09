import unittest

from .utils import setUpModule


class ListNodeTest(unittest.TestCase):
    def test_access(self):
        from yamlfig.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])
        self.assertEqual(test[0], 1)
        self.assertEqual(test[1], 2)
        self.assertEqual(test[2], 3)
        self.assertEqual(test[-1], 3)

        self.assertEqual(test.node_info.get_child(0), 1)
        self.assertEqual(test.node_info.get_child(1), 2)
        self.assertEqual(test.node_info.get_child(2), 3)
        self.assertEqual(test.node_info.get_child(-1), 3)
        self.assertIs(test.node_info.get_child(4, None), None)
        self.assertEqual(test.node_info.children_count(), 3)

        with self.assertRaises(IndexError):
            _ = test[4]

        with self.assertRaises(TypeError):
            _ = test['name']

        with self.assertRaises(TypeError):
            _ = test['0']

        with self.assertRaises(TypeError):
            _ = test[0.0]

        with self.assertRaises(AttributeError):
            _ = getattr(test, '0')

        with self.assertRaises(TypeError):
            _ = getattr(test, 4)

        with self.assertRaises(TypeError):
            _ = getattr(test, -1)

        with self.assertRaises(AttributeError):
            _ = getattr(test, 'name')

        with self.assertRaises(TypeError):
            _ = getattr(test, 0.0)

        self.assertTrue(isinstance(test, list))
        self.assertEqual(len(test),  3)

    def test_set(self):
        from yamlfig.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])

        test[0] = 11
        test[1] = 22
        test[2] = 33
        self.assertEqual(test.node_info.get_child(0), 11)
        self.assertEqual(test.node_info.get_child(1), 22)
        self.assertEqual(test.node_info.get_child(2), 33)

        test.node_info.set_child(0, 111)
        test.node_info.set_child(1, 222)
        test.node_info.set_child(2, 333)
        self.assertEqual(test[0], 111)
        self.assertEqual(test[1], 222)
        self.assertEqual(test[2], 333)

        test[-1] = 44
        self.assertEqual(test[-1], 44)
        self.assertEqual(test[2], 44)

        with self.assertRaises(IndexError):
            test[3] = 55

        test.append(55)
        self.assertEqual(test.node_info.get_child(3), 55)

    def test_del(self):
        from yamlfig.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])
        del test[1]
        self.assertEqual(test[0], 1)
        self.assertEqual(test[1], 3)
        self.assertEqual(len(test), 2)
        self.assertTrue(test.node_info.has_child(1))
        self.assertFalse(test.node_info.has_child(2))

        del test[-1]
        self.assertEqual(test[0], 1)
        self.assertEqual(len(test), 1)
        self.assertTrue(test.node_info.has_child(0))
        self.assertFalse(test.node_info.has_child(1))

        with self.assertRaisesRegex(ValueError, expected_regex=r'4 is not in list'):
            test.remove(4)
        self.assertEqual(test[0], 1)
        self.assertEqual(len(test), 1)

        test.remove(1)
        self.assertFalse(test.node_info.has_child(0))
        self.assertIs(test.node_info.get_child(0, None), None)
        self.assertEqual(test.node_info.children_count(), 0)


if __name__ == '__main__':
    unittest.main()
