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

import unittest

from .utils import setUpModule
from awesomeyaml.config import Config


class CmdlineTest(unittest.TestCase):
    def test_simple(self):
        cfg = Config.build_from_cmdline("{ foo: 12 }", "foo=1")
        self.assertEqual(cfg.foo, 1)

    def test_overwrite_list_item(self):
        cfg = Config.build_from_cmdline("{ foo: [1,2] }", "foo[1]=3")
        self.assertEqual(cfg.foo, [1,3])

    def test_overwrite_list_item_complex(self):
        cfg = Config.build_from_cmdline("{ foo: [-1, { test: 12 }, 10] }", "{ foo: !merge [1, !del { bar: [[[[2]]]] }] }", "foo[1].bar[0][0][0][0]=3")
        self.assertEqual(cfg.foo[0], 1)
        self.assertNotIn('test', cfg.foo[1])
        self.assertEqual(cfg.foo[1].bar[0][0][0][0], 3)
        self.assertEqual(cfg.foo[2], 10)

    def test_typo(self):
        with self.assertRaisesRegex(ValueError, r"Node 'fooo' .*"):
            _ = Config.build_from_cmdline("{ foo: 12 }", "fooo=1")

    def test_explicit_not_typo(self):
        cfg = Config.build_from_cmdline("{ foo: 12 }", "!new fooo=1")
        self.assertEqual(cfg.foo, 12)
        self.assertEqual(cfg.fooo, 1)

    def test_missing_nested(self):
        with self.assertRaisesRegex(ValueError, r"Node 'foo.bar[2]' .*"):
            _ = Config.build_from_cmdline("{ foo: { bar: [1, 2] }}", "foo.bar[2]=3")



if __name__ == '__main__':
    unittest.main()
