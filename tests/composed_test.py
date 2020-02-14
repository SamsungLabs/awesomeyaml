import unittest

from .utils import setUpModule


class ComposedNodeTest(unittest.TestCase):
    def setUp(self):
        from yamlfig.nodes.composed import ComposedNode
        self.test = ComposedNode({ 0: 1, 1: 2, 2: 3 })

    def tearDown(self):
        self.test = None

    def test_get_child(self):
        self.assertEqual(self.test.yamlfigns.get_child(0), 1)
        self.assertEqual(self.test.yamlfigns.get_child(1), 2)
        self.assertEqual(self.test.yamlfigns.get_child(2), 3)
        self.assertIs(self.test.yamlfigns.get_child(4, None), None)

    def test_children_count(self):
        self.assertEqual(self.test.yamlfigns.children_count(), 3)
        self.assertEqual(self.test.yamlfigns.children_count(), len(self.test._children))

    def test_has_child(self):
        self.assertTrue(self.test.yamlfigns.has_child(0))
        self.assertTrue(self.test.yamlfigns.has_child(1))
        self.assertTrue(self.test.yamlfigns.has_child(2))
        self.assertFalse(self.test.yamlfigns.has_child(3))
        self.assertFalse(self.test.yamlfigns.has_child(-20))

    def test_set_child(self):
        self.test.yamlfigns.set_child(0, 111)
        self.test.yamlfigns.set_child(1, 222)
        self.test.yamlfigns.set_child(2, 333)
        self.assertEqual(self.test.yamlfigns.get_child(0), 111)
        self.assertEqual(self.test.yamlfigns.get_child(1), 222)
        self.assertEqual(self.test.yamlfigns.get_child(2), 333)

    def test_remove_child(self):
        self.test.yamlfigns.remove_child(1)
        self.assertFalse(self.test.yamlfigns.has_child(1))
        self.assertEqual(self.test.yamlfigns.children_count(), 2)

    def test_rename_child(self):
        self.assertFalse(self.test.yamlfigns.has_child(5))
        before = self.test.yamlfigns.get_child(2)
        self.test.yamlfigns.rename_child(2, 5)
        self.assertTrue(self.test.yamlfigns.has_child(5))
        after = self.test.yamlfigns.get_child(5)
        self.assertIs(before, after)

    def test_get_node(self):
        self.assertIs(self.test.yamlfigns.get_node('[0]'), self.test._children[0])
        self.assertIs(self.test.yamlfigns.get_node(0), self.test._children[0])
        self.assertIs(self.test.yamlfigns.get_node([0]), self.test._children[0])

        self.assertIs(self.test.yamlfigns.get_node(), self.test)
        self.assertIs(self.test.yamlfigns.get_node(''), self.test)
        self.assertIs(self.test.yamlfigns.get_node(None), self.test)
        self.assertIs(self.test.yamlfigns.get_node([]), self.test)

    def test_get_missing_nodes(self):
        self.assertIsNone(self.test.yamlfigns.get_node(12, incomplete=None))
        self.assertIsNone(self.test.yamlfigns.get_node(12, incomplete=True))
        with self.assertRaises(KeyError):
            _ = self.test.yamlfigns.get_node(12, incomplete=False)

    def test_get_nodes_with_names(self):
        node, name, path = self.test.yamlfigns.get_node(0, names=True)
        self.assertIs(node, self.test._children[0])
        self.assertEqual(name, 0)
        self.assertEqual(path, [0])

    def test_get_all_nodes(self):
        nodes = self.test.yamlfigns.get_node(0, intermediate=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0], self.test)
        self.assertIs(nodes[1], self.test._children[0])

    def test_get_all_nodes_with_paths(self):
        nodes = self.test.yamlfigns.get_node(0, intermediate=True, names=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0][0], self.test)
        self.assertIs(nodes[0][1], None)
        self.assertEqual(nodes[0][2], [])
        self.assertIs(nodes[1][0], self.test._children[0])
        self.assertEqual(nodes[1][1], 0)
        self.assertEqual(nodes[1][2], [0])

    def test_get_all_nodes_with_paths_missing(self):
        nodes = self.test.yamlfigns.get_node(12, intermediate=True, names=True, incomplete=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0][0], self.test)
        self.assertIs(nodes[0][1], None)
        self.assertEqual(nodes[0][2], [])
        self.assertIs(nodes[1][0], None)
        self.assertEqual(nodes[1][1], 12)
        self.assertEqual(nodes[1][2], [12])

    def test_children(self):
        count = 0
        for child in self.test.yamlfigns.children():
            self.assertIn(child, self.test._children.values())
            count += 1
        self.assertEqual(count, self.test.yamlfigns.children_count())
        
    def test_named_children(self):
        count = 0
        for name, child in self.test.yamlfigns.named_children():
            self.assertIn(name, self.test._children)
            self.assertIn(child, self.test._children.values())
            self.assertIs(child, self.test.yamlfigns.get_child(name))
            count += 1
        self.assertEqual(count, self.test.yamlfigns.children_count())

    def test_nodes(self):
        count = 0
        for child in self.test.yamlfigns.nodes(include_self=False):
            self.assertIn(child, self.test._children.values())
            count += 1
        self.assertEqual(count, self.test.yamlfigns.children_count())

        with_self = list(self.test.yamlfigns.nodes(include_self=True))
        self.assertEqual(count+1, len(with_self))
        self.assertIs(with_self[0], self.test)

    def test_nodes_with_paths(self):
        from yamlfig.nodes.composed import ComposedNode
        count = 0
        for path, node in self.test.yamlfigns.nodes_with_paths(include_self=False):
            self.assertEqual(len(path), 1)
            name = path[0]
            self.assertIn(name, self.test._children)
            self.assertIn(node, self.test._children.values())
            self.assertIs(node, self.test.yamlfigns.get_child(name))
            count += 1
        self.assertEqual(count, self.test.yamlfigns.children_count())

        with_self = list(self.test.yamlfigns.nodes_with_paths(include_self=True))
        self.assertEqual(count+1, len(with_self))
        self.assertIs(with_self[0][1], self.test)

    def test_clear(self):
        self.assertEqual(self.test.yamlfigns.children_count(), 3)
        self.assertTrue(self.test.yamlfigns.has_child(1))
        self.test.yamlfigns.clear()
        self.assertEqual(self.test.yamlfigns.children_count(), 0)
        self.assertFalse(self.test.yamlfigns.has_child(1))


class ComposedNodeNamesAndPathsTest(unittest.TestCase):
    def setUp(self):
        from yamlfig.nodes.node import ConfigNode
        from yamlfig.nodes.composed import ComposedNode
        dup_str = 'duplicate'
        self.test = ComposedNode({
            0: 0,
            '0': '0',
            1: { 0: dup_str, '1': 'test1' },
            '1': { '0': dup_str, 1: 'test2' },
            -1: dup_str,
            -2: dup_str
        })

        assert self.test.yamlfigns.get_child(-1) is self.test.yamlfigns.get_child(-2)

    def tearDown(self):
        self.test = None

    def test_dup_children(self):
        all_children = list(self.test.yamlfigns.children(allow_duplicates=True))
        unique_children = list(self.test.yamlfigns.children(allow_duplicates=False))
        self.assertEqual(len(all_children) - 1, len(unique_children))

    def test_dup_nodes(self):
        all_nodes = list(self.test.yamlfigns.nodes(allow_duplicates=True))
        unique_nodes = list(self.test.yamlfigns.nodes(allow_duplicates=False))
        self.assertEqual(len(all_nodes) - 3, len(unique_nodes))

    def test_get_node(self):
        # access int
        self.assertIs(self.test.yamlfigns.get_node('[0]'), self.test._children[0])
        self.assertIs(self.test.yamlfigns.get_node(0), self.test._children[0])
        self.assertIs(self.test.yamlfigns.get_node([0]), self.test._children[0])

        # access str
        self.assertIs(self.test.yamlfigns.get_node('0'), self.test._children['0'])
        self.assertIs(self.test.yamlfigns.get_node(['0']), self.test._children['0'])

        # access int,int
        self.assertIs(self.test.yamlfigns.get_node('[1][0]'), self.test._children[1]._children[0])
        self.assertIs(self.test.yamlfigns.get_node(1, 0), self.test._children[1]._children[0])
        self.assertIs(self.test.yamlfigns.get_node([1, 0]), self.test._children[1]._children[0])

        # access int,str
        self.assertIs(self.test.yamlfigns.get_node('[1].1'), self.test._children[1]._children['1'])
        self.assertIs(self.test.yamlfigns.get_node(1, '1'), self.test._children[1]._children['1'])
        self.assertIs(self.test.yamlfigns.get_node([1, '1']), self.test._children[1]._children['1'])

        # access str,str
        self.assertIs(self.test.yamlfigns.get_node('1.0'), self.test._children['1']._children['0'])
        self.assertIs(self.test.yamlfigns.get_node('1', '0'), self.test._children['1']._children['0'])
        self.assertIs(self.test.yamlfigns.get_node(['1', '0']), self.test._children['1']._children['0'])

        # access str,int
        self.assertIs(self.test.yamlfigns.get_node('1[1]'), self.test._children['1']._children[1])
        self.assertIs(self.test.yamlfigns.get_node('1', 1), self.test._children['1']._children[1])
        self.assertIs(self.test.yamlfigns.get_node(['1', 1]), self.test._children['1']._children[1])

    def test_get_missing_nodes(self):
        self.assertIsNone(self.test.yamlfigns.get_node(0, 100, incomplete=None))
        self.assertIsNone(self.test.yamlfigns.get_node(0, 100, incomplete=None))
        self.assertIsNone(self.test.yamlfigns.get_node(12, incomplete=True))
        with self.assertRaises(KeyError):
            _ = self.test.yamlfigns.get_node(12, incomplete=False)

    def test_get_nodes_with_names(self):
        node, name, path = self.test.yamlfigns.get_node(0, names=True)
        self.assertIs(node, self.test._children[0])
        self.assertEqual(name, 0)
        self.assertEqual(path, [0])

    def test_get_all_nodes(self):
        nodes = self.test.yamlfigns.get_node(0, intermediate=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0], self.test)
        self.assertIs(nodes[1], self.test._children[0])

    def test_get_all_nodes_with_paths(self):
        nodes = self.test.yamlfigns.get_node(0, intermediate=True, names=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0][0], self.test)
        self.assertIs(nodes[0][1], None)
        self.assertEqual(nodes[0][2], [])
        self.assertIs(nodes[1][0], self.test._children[0])
        self.assertEqual(nodes[1][1], 0)
        self.assertEqual(nodes[1][2], [0])

    def test_get_all_nodes_with_paths_missing(self):
        nodes = self.test.yamlfigns.get_node(12, intermediate=True, names=True, incomplete=True)
        self.assertEqual(len(nodes), 2)
        self.assertIs(nodes[0][0], self.test)
        self.assertIs(nodes[0][1], None)
        self.assertEqual(nodes[0][2], [])
        self.assertIs(nodes[1][0], None)
        self.assertEqual(nodes[1][1], 12)
        self.assertEqual(nodes[1][2], [12])

class ComposedNodeNestedTest(unittest.TestCase):
    def setUp(self):
        from yamlfig.nodes.composed import ComposedNode
        dup_int = 12
        self.test = ComposedNode({ 0: ComposedNode({ 'foo': -1, 'bar': -2, 5: dup_int }), 1: 2, '5': dup_int })

    def tearDown(self):
        self.test = None


if __name__ == '__main__':
    unittest.main()
