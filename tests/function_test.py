import copy
import pickle
import unittest

from .utils import setUpModule


def test_f(a, b):
    return a**2 + b


class FunctionNodeTest(unittest.TestCase):
    def test_copy(self):
        from yamlfig.nodes.function import FunctionNode
        test = FunctionNode(test_f, args={ 'a': 3, 'b': 2 })
        test2 = copy.copy(test)
        self.assertEqual(test, test2)
        self.assertIsNot(test, test2)
        self.assertIs(test.a, test2.a)
        self.assertIsInstance(test2, FunctionNode)
        self.assertEqual(test._func(**test), 11)
        self.assertEqual(test2._func(**test2), 11)

    def test_deepcopy(self):
        from yamlfig.nodes.function import FunctionNode
        test = FunctionNode(test_f, args={ 'a': 3, 'b': 2 })
        test2 = copy.deepcopy(test)
        self.assertEqual(test, test2)
        self.assertIsNot(test, test2)
        self.assertIsNot(test.a, test2.a)
        self.assertIsInstance(test2, FunctionNode)
        self.assertEqual(test._func(**test), 11)
        self.assertEqual(test2._func(**test2), 11)

    def test_pickle(self):
        from yamlfig.nodes.function import FunctionNode
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
