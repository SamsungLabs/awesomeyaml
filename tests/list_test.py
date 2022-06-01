# Copyright 2022 Samsung Electronics Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
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

        self.assertEqual(test.yamlfigns.get_child(0), 1)
        self.assertEqual(test.yamlfigns.get_child(1), 2)
        self.assertEqual(test.yamlfigns.get_child(2), 3)
        self.assertEqual(test.yamlfigns.get_child(-1), 3)
        self.assertIs(test.yamlfigns.get_child(4, None), None)
        self.assertEqual(test.yamlfigns.children_count(), 3)

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
        self.assertEqual(test.yamlfigns.get_child(0), 11)
        self.assertEqual(test.yamlfigns.get_child(1), 22)
        self.assertEqual(test.yamlfigns.get_child(2), 33)

        test.yamlfigns.set_child(0, 111)
        test.yamlfigns.set_child(1, 222)
        test.yamlfigns.set_child(2, 333)
        self.assertEqual(test[0], 111)
        self.assertEqual(test[1], 222)
        self.assertEqual(test[2], 333)

        test[-1] = 44
        self.assertEqual(test[-1], 44)
        self.assertEqual(test[2], 44)

        with self.assertRaises(IndexError):
            test[3] = 55

        test.append(55)
        self.assertEqual(test.yamlfigns.get_child(3), 55)

    def test_del(self):
        from yamlfig.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])
        del test[1]
        self.assertEqual(test[0], 1)
        self.assertEqual(test[1], 3)
        self.assertEqual(len(test), 2)
        self.assertTrue(test.yamlfigns.has_child(1))
        self.assertFalse(test.yamlfigns.has_child(2))

        del test[-1]
        self.assertEqual(test[0], 1)
        self.assertEqual(len(test), 1)
        self.assertTrue(test.yamlfigns.has_child(0))
        self.assertFalse(test.yamlfigns.has_child(1))

        with self.assertRaisesRegex(ValueError, expected_regex=r'4 is not in list'):
            test.remove(4)
        self.assertEqual(test[0], 1)
        self.assertEqual(len(test), 1)

        test.remove(1)
        self.assertFalse(test.yamlfigns.has_child(0))
        self.assertIs(test.yamlfigns.get_child(0, None), None)
        self.assertEqual(test.yamlfigns.children_count(), 0)

    def test_extend(self):
        from yamlfig.nodes.list import ConfigList
        l1 = ConfigList([1, 2])
        l2 = ConfigList([3, 4])
        l1.extend(l2)
        self.assertEqual(l1, [1, 2, 3, 4])
        self.assertEqual(l1[-1], 4)
        self.assertEqual(l1.yamlfigns.children_count(), 4)

    def test_copy(self):
        from yamlfig.nodes.list import ConfigList
        test = ConfigList([1, 2, [3, 4]])
        c = copy.copy(test)
        self.assertIsNot(test, c)
        self.assertEqual(test, c)
        self.assertEqual(test.yamlfigns.node_info, c.yamlfigns.node_info)
        for path, node in test.yamlfigns.nodes_with_paths(include_self=False):
            node2 = c.yamlfigns.get_node(path)
            self.assertIs(node, node2)
            self.assertEqual(node, node2)
            self.assertEqual(node.yamlfigns.node_info, node2.yamlfigns.node_info)

    def test_deepcopy(self):
        from yamlfig.nodes.list import ConfigList
        test = ConfigList([1, 2, [3, 4]])
        c = copy.deepcopy(test)
        self.assertIsNot(test, c)
        self.assertEqual(test, c)
        self.assertEqual(test.yamlfigns.node_info, c.yamlfigns.node_info)
        for path, node in test.yamlfigns.nodes_with_paths(include_self=False):
            node2 = c.yamlfigns.get_node(path)
            self.assertIsNot(node, node2)
            self.assertEqual(node, node2)
            self.assertEqual(node.yamlfigns.node_info, node2.yamlfigns.node_info)


if __name__ == '__main__':
    unittest.main()
