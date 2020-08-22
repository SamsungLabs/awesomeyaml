import pickle
import unittest

from .utils import setUpModule


class PickleTest(unittest.TestCase):
    def check_pickle(self, obj, composed=False):
        _obj = pickle.dumps(obj)
        obj_ = pickle.loads(_obj)
        self.assertIsNot(obj, obj_)
        self.assertEqual(obj, obj_)
        self.assertEqual(obj.yamlfigns.node_info, obj_.yamlfigns.node_info)
        if composed:
            for path, node in obj.yamlfigns.nodes_with_paths():
                node_ = obj_.yamlfigns.get_node(path)
                self.assertIsNot(node, node_)
                self.assertEqual(node, node_)
                self.assertEqual(node.yamlfigns.node_info, node_.yamlfigns.node_info)

    def test_scalar(self):
        from yamlfig.nodes.scalar import ConfigScalar

        test = ConfigScalar(1)
        self.check_pickle(test)

        test = ConfigScalar(0.1)
        self.check_pickle(test)

        test = ConfigScalar('placki')
        self.check_pickle(test)

        test = ConfigScalar(True)
        self.check_pickle(test)

        test = ConfigScalar(None)
        self.check_pickle(test)

    def test_list(self):
        from yamlfig.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])
        self.check_pickle(test, composed=True)

    def test_dict(self):
        from yamlfig.nodes.dict import ConfigDict

        test = ConfigDict({ 'test': False, 1: None })
        self.check_pickle(test, composed=True)


if __name__ == '__main__':
    unittest.main()
