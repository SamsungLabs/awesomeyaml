import unittest

from .utils import setUpModule


class SimpleTest(unittest.TestCase):
    def setUp(self):
        self.data = {
            'test': 1,
            'test2': 12,
            'test3': False,
            'test4': {
                'foo': 'placki',
                'bar': [ 'A', 'B', 'C']
            }
        }

    def test_empty_config(self):
        from yamlfig.config import Config
        cfg = Config()
        self.assertEqual(len(cfg), 0)

    def test_config(self):
        from yamlfig.config import Config
        cfg = Config(self.data)
        self.assertEqual(cfg.test, 1)
        self.assertEqual(cfg.test2, 12)
        self.assertEqual(cfg.test3, False)
        self.assertEqual(cfg.test4['foo'], 'placki')
        self.assertEqual(cfg.test4.bar[1], 'B')
        self.assertTrue('test' in cfg)
        
        cfg.test = (1, 2)
        self.assertEqual(cfg['test'], (1,2))

        del cfg.test2
        self.assertTrue('test2' not in cfg)

        cfg.test2 = 13
        self.assertTrue(cfg['test2'] == cfg.test2 == 13)


if __name__ == '__main__':
    unittest.main()
