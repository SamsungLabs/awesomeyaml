import unittest

from .utils import setUpModule


class CreateFromFileTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_content = '''
            test:
                bar: 12
                foo: 13

            test2:
                foo: False
                bar: True
        '''

    def _check_test_obj(self, cfg):
        self.assertEqual(cfg.test.bar, 12)
        self.assertEqual(cfg.test.foo, 13)
        self.assertEqual(cfg.test2.foo, False)
        self.assertEqual(cfg.test2.bar, True)

    def test_yaml(self):
        import io
        from yamlfig.config import Config
        cfg = Config(self._file_content)
        self._check_test_obj(cfg)

    def test_filename(self):
        import os
        import tempfile
        from yamlfig.config import Config
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        try:
            fp.write(self._file_content)
            fp.flush()
            fp.close()
            cfg = Config(fp.name)
            self._check_test_obj(cfg)
        finally:
            os.unlink(fp.name)

    def test_fileobj(self):
        import tempfile
        from yamlfig.config import Config
        with tempfile.TemporaryFile(mode='w+') as fp:
            fp.write(self._file_content)
            fp.flush()
            fp.seek(0)
            cfg = Config(fp)
            self._check_test_obj(cfg)


if __name__ == '__main__':
    unittest.main()
