import unittest

from .utils import setUpModule


class DictNodeTest(unittest.TestCase):
    def test_access(self):
        from yamlfig.nodes.dict import ConfigDict

        test = ConfigDict({ 'k1': 1, 'k2': 2, 'k3': 3 })
        self.assertEqual(test['k1'], 1)
        self.assertEqual(test['k2'], 2)
        self.assertEqual(test['k3'], 3)
        with self.assertRaises(KeyError):
            _ = test['k4']

        self.assertTrue('k1' in test)
        self.assertFalse('k2' not in test)

        self.assertEqual(test.k1, 1)
        self.assertEqual(test.k2, 2)
        self.assertEqual(test.k3, 3)
        with self.assertRaises(AttributeError):
            _ = test.k4

        self.assertEqual(test.yamlfigns.get_child('k1'), 1)
        self.assertEqual(test.yamlfigns.get_child('k2'), 2)
        self.assertEqual(test.yamlfigns.get_child('k3'), 3)
        self.assertIs(test.yamlfigns.get_child('k4', None), None)
        self.assertEqual(test.yamlfigns.children_count(), 3)

        self.assertTrue(isinstance(test, dict))
        self.assertEqual(len(test),  3)

    def test_access2(self):
        from yamlfig.nodes.dict import ConfigDict

        test = ConfigDict({ i: i**2 for i in range(3) })
        self.assertTrue(0 in test)
        self.assertTrue(5 not in test)

        self.assertEqual(test[2], 4)
        with self.assertRaises(TypeError):
            _ = getattr(test, 0)


    def test_set(self):
        from yamlfig.nodes.dict import ConfigDict

        test = ConfigDict({ 'k1': 1, 'k2': 2, 'k3': 3 })

        test['k1'] = 11
        test['k2'] = 22
        test['k3'] = 33
        self.assertEqual(test.yamlfigns.get_child('k1'), 11)
        self.assertEqual(test.yamlfigns.get_child('k2'), 22)
        self.assertEqual(test.yamlfigns.get_child('k3'), 33)
        self.assertEqual(test.k1, 11)
        self.assertEqual(test.k2, 22)
        self.assertEqual(test.k3, 33)

        test.yamlfigns.set_child('k1', 111)
        test.yamlfigns.set_child('k2', 222)
        test.yamlfigns.set_child('k3', 333)
        self.assertEqual(test['k1'], 111)
        self.assertEqual(test['k2'], 222)
        self.assertEqual(test['k3'], 333)
        self.assertEqual(test.k1, 111)
        self.assertEqual(test.k2, 222)
        self.assertEqual(test.k3, 333)

        test.k1 = 1111
        test.k2 = 2222
        test.k3 = 3333
        self.assertEqual(test['k1'], 1111)
        self.assertEqual(test['k2'], 2222)
        self.assertEqual(test['k3'], 3333)
        self.assertEqual(test.yamlfigns.get_child('k1'), 1111)
        self.assertEqual(test.yamlfigns.get_child('k2'), 2222)
        self.assertEqual(test.yamlfigns.get_child('k3'), 3333)

        test[-1] = 44
        self.assertEqual(test[-1], 44)
        self.assertEqual(test.yamlfigns.get_child(-1), 44)

        test['k4'] = 55
        self.assertEqual(test['k4'], 55)
        self.assertEqual(test.yamlfigns.get_child('k4'), 55)
        self.assertEqual(test.k4, 55)

        test.k5 = 66
        self.assertEqual(test['k5'], 66)
        self.assertEqual(test.yamlfigns.get_child('k5'), 66)
        self.assertEqual(test.k5, 66)

        test.yamlfigns.set_child('k6', 77)
        self.assertEqual(test['k6'], 77)
        self.assertEqual(test.yamlfigns.get_child('k6'), 77)
        self.assertEqual(test.k6, 77)

        test.setdefault('k7', 88)
        self.assertEqual(test['k7'], 88)
        self.assertEqual(test.yamlfigns.get_child('k7'), 88)
        self.assertEqual(test.k7, 88)

        test.setdefault('k7', 99)
        self.assertEqual(test['k7'], 88)
        self.assertEqual(test.yamlfigns.get_child('k7'), 88)
        self.assertEqual(test.k7, 88)

    def test_del(self):
        from yamlfig.nodes.dict import ConfigDict

        test = ConfigDict({ 'k1': 1, 'k2': 2, 'k3': 3 })
        del test['k1']
        self.assertFalse('k1' in test)
        self.assertFalse(test.yamlfigns.has_child('k1'))
        self.assertEqual(len(test), 2)
        self.assertTrue(test.yamlfigns.has_child('k2'))
        self.assertTrue(test.yamlfigns.has_child('k3'))

        with self.assertRaisesRegex(KeyError, expected_regex=r'k5'):
            test.pop('k5')

        self.assertEqual(len(test), 2)
        self.assertTrue(test.yamlfigns.has_child('k2'))
        self.assertTrue(test.yamlfigns.has_child('k3'))

        val = test.pop('k3')
        self.assertEqual(len(test), 1)
        self.assertEqual(val, 3)

        val = test.pop('k3', None)
        self.assertIs(val, None)
        self.assertEqual(len(test), 1)

    def test_filter(self):
        from yamlfig.nodes.dict import ConfigDict
        test = ConfigDict({ 'a': 1, 'b': 2, 'c': { 'd': 3, 'e': 4 } })
        filtered = test.yamlfigns.filter_nodes(lambda path, node: not isinstance(node, int) or node % 2 == 0)
        self.assertEqual(filtered, { 'b': 2, 'c': { 'e': 4 }})

    def test_map(self):
        from yamlfig.nodes.dict import ConfigDict
        test = ConfigDict({ 'a': 1, 'b': 2, 'c': { 'd': 3, 'e': 4 } })
        mapped = test.yamlfigns.map_nodes(lambda path, node: node**2)
        self.assertEqual(mapped, { 'a': 1, 'b': 4, 'c': { 'd': 9, 'e': 16 }})

    def test_copy(self):
        from yamlfig.nodes.dict import ConfigDict
        test = ConfigDict({ 'a': 1, 'b': 2, 'c': { 'd': 3, 'e': 4 } })
        c = test.yamlfigns.copy()
        self.assertIsNot(test, c)
        for path, node in test.yamlfigns.nodes_with_paths(include_self=False):
            node2 = c.yamlfigns.get_node(path)
            self.assertIs(node, node2)

    def test_deepcopy(self):
        from yamlfig.nodes.dict import ConfigDict
        test = ConfigDict({ 'a': 1, 'b': 2, 'c': { 'd': 3, 'e': 4 } })
        c = test.yamlfigns.deepcopy()
        self.assertIsNot(test, c)
        for path, node in test.yamlfigns.nodes_with_paths(include_self=False):
            node2 = c.yamlfigns.get_node(path)
            self.assertIsNot(node, node2)

if __name__ == '__main__':
    unittest.main()
