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
import pickle
import unittest

from .utils import setUpModule


def test_f(a, b):
    return a**2 + b


class FunctionNodeTest(unittest.TestCase):
    def test_copy(self):
        from awesomeyaml.nodes.function import FunctionNode
        test = FunctionNode(test_f, args={ 'a': 3, 'b': 2 })
        test2 = copy.copy(test)
        self.assertEqual(test, test2)
        self.assertIsNot(test, test2)
        self.assertIs(test.a, test2.a)
        self.assertIsInstance(test2, FunctionNode)
        self.assertEqual(test._func(**test), 11)
        self.assertEqual(test2._func(**test2), 11)

    def test_deepcopy(self):
        from awesomeyaml.nodes.function import FunctionNode
        test = FunctionNode(test_f, args={ 'a': 3, 'b': 2 })
        test2 = copy.deepcopy(test)
        self.assertEqual(test, test2)
        self.assertIsNot(test, test2)
        self.assertIsNot(test.a, test2.a)
        self.assertIsInstance(test2, FunctionNode)
        self.assertEqual(test._func(**test), 11)
        self.assertEqual(test2._func(**test2), 11)

    def test_pickle(self):
        from awesomeyaml.nodes.function import FunctionNode
        test = FunctionNode(test_f, args={ 'a': 3, 'b': 2 })
        test2 = pickle.loads(pickle.dumps(test))
        self.assertEqual(test, test2)
        self.assertIsNot(test, test2)
        self.assertIsNot(test.a, test2.a)
        self.assertIsInstance(test2, FunctionNode)
        self.assertEqual(test._func(**test), 11)
        self.assertEqual(test2._func(**test2), 11)

if __name__ == '__main__':
    unittest.main()
