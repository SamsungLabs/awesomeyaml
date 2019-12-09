import unittest

from .utils import setUpModule


class ComposedNodeTest(unittest.TestCase):
    def setUp(self):
        from yamlfig.nodes.composed import ComposedNode
        self.test = ComposedNode({ 0: 1, 1: 2, 2: 3 })

    def tearDown(self):
        self.test = None

    def test_get_child(self):
        self.assertEqual(self.test.node_info.get_child(0), 1)
        self.assertEqual(self.test.node_info.get_child(1), 2)
        self.assertEqual(self.test.node_info.get_child(2), 3)
        self.assertIs(self.test.node_info.get_child(4, None), None)

    def test_children_count(self):
        self.assertEqual(self.test.node_info.children_count(), 3)
        self.assertEqual(self.test.node_info.children_count(), len(self.test._children))

    def test_has_child(self):
        self.assertTrue(self.test.node_info.has_child(0))
        self.assertTrue(self.test.node_info.has_child(1))
        self.assertTrue(self.test.node_info.has_child(2))
        self.assertFalse(self.test.node_info.has_child(3))
        self.assertFalse(self.test.node_info.has_child(-20))

    def test_set_child(self):
        self.test.node_info.set_child(0, 111)
        self.test.node_info.set_child(1, 222)
        self.test.node_info.set_child(2, 333)
        self.assertEqual(self.test.node_info.get_child(0), 111)
        self.assertEqual(self.test.node_info.get_child(1), 222)
        self.assertEqual(self.test.node_info.get_child(2), 333)

    def test_remove_child(self):
        self.test.node_info.remove_child(1)
        self.assertFalse(self.test.node_info.has_child(1))
        self.assertEqual(self.test.node_info.children_count(), 2)

    def test_rename_child(self):
        self.assertFalse(self.test.node_info.has_child(5))
        before = self.test.node_info.get_child(2)
        self.test.node_info.rename_child(2, 5)
        self.assertTrue(self.test.node_info.has_child(5))
        after = self.test.node_info.get_child(5)
        self.assertIs(before, after)

    def test_get_node(self):
        self.assertIs(self.test.node_info.get_node([0]))

    def test_children(self):
        count = 0
        for child in self.test.node_info.children():
            self.assertIn(child, self.test._children.values())
            count += 1
        self.assertEqual(count, self.test.node_info.children_count())
        
    def test_named_children(self):
        count = 0
        for name, child in self.test.node_info.named_children():
            self.assertIn(name, self.test._children)
            self.assertIn(child, self.test._children.values())
            self.assertIs(child, self.test.node_info.get_child(name))
            count += 1
        self.assertEqual(count, self.test.node_info.children_count())

    def test_nodes(self):
        count = 0
        for child in self.test.node_info.nodes(include_self=False):
            self.assertIn(child, self.test._children.values())
            count += 1
        self.assertEqual(count, self.test.node_info.children_count())

        with_self = list(self.test.node_info.nodes())
        self.assertEqual(count+1, len(with_self))
        self.assertIs(with_self[0], self.test)

    def test_named_nodes(self):
        count = 0
        for name, child in self.test.node_info.named_nodes(include_self=False):
            self.assertIn(int(name), self.test._children)
            self.assertIn(child, self.test._children.values())
            self.assertIs(child, self.test.node_info.get_child(int(name)))
            count += 1
        self.assertEqual(count, self.test.node_info.children_count())

        with_self = list(self.test.node_info.named_nodes())
        self.assertEqual(count+1, len(with_self))
        self.assertIs(with_self[0][1], self.test)

    def test_clear(self):
        self.assertEqual(self.test.node_info.children_count(), 3)
        self.assertTrue(self.test.node_info.has_child(1))
        self.test.node_info.clear()
        self.assertEqual(self.test.node_info.children_count(), 0)
        self.assertFalse(self.test.node_info.has_child(1))


class ComposedNodeNestedTest(unittest.TestCase):
    def setUp(self):
        from yamlfig.nodes.composed import ComposedNode
        self.test = ComposedNode({ 0: ComposedNode({ 'foo': -1, 'bar': -2 }), 1: 2 })

    def tearDown(self):
        self.test = None

    


if __name__ == '__main__':
    unittest.main()
