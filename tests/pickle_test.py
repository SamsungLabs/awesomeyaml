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

import pickle
import unittest

from .utils import setUpModule


class PickleTest(unittest.TestCase):
    def check_pickle(self, obj, composed=False):
        _obj = pickle.dumps(obj)
        obj_ = pickle.loads(_obj)
        self.assertIsNot(obj, obj_)
        self.assertEqual(obj, obj_)
        self.assertEqual(obj.ayns.node_info, obj_.ayns.node_info)
        if composed:
            for path, node in obj.ayns.nodes_with_paths():
                node_ = obj_.ayns.get_node(path)
                self.assertIsNot(node, node_)
                self.assertEqual(node, node_)
                self.assertEqual(node.ayns.node_info, node_.ayns.node_info)

    def test_scalar(self):
        from awesomeyaml.nodes.scalar import ConfigScalar

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
        from awesomeyaml.nodes.list import ConfigList

        test = ConfigList([1, 2, 3])
        self.check_pickle(test, composed=True)

    def test_dict(self):
        from awesomeyaml.nodes.dict import ConfigDict

        test = ConfigDict({ 'test': False, 1: None })
        self.check_pickle(test, composed=True)


if __name__ == '__main__':
    unittest.main()
