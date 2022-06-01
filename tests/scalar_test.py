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


class ScalarNodeIntTest(unittest.TestCase):
    def test_str(self):
        from yamlfig.nodes.scalar import ConfigScalar
        i = ConfigScalar(12)
        self.assertEqual(str(i), str(12))

    def test_types(self):
        from yamlfig.nodes.scalar import ConfigScalar
        i = ConfigScalar(12)
        self.assertIsInstance(i, int)
        self.assertIsInstance(i, ConfigScalar)
        self.assertIsInstance(i, ConfigScalar(int))
        self.assertIs(type(i), ConfigScalar(int))
        self.assertTrue(issubclass(ConfigScalar(int), ConfigScalar))

    def test_arithmetic_ops(self):
        from yamlfig.nodes.scalar import ConfigScalar
        i = ConfigScalar(12)
        self.assertEqual(str(i), '12')
        i2 = i**2
        self.assertEqual(i2, 144)

if __name__ == '__main__':
    unittest.main()
