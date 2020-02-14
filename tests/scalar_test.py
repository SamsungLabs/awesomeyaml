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
