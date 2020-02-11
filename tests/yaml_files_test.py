import unittest
import os

from .utils import setUpModule


class YamlFileTest():
    def __init__(self, test_file, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

        self.test_yaml = []
        self.expected_result = []
        test_input = True
        with open(test_file, 'r') as test:
            for line in test:
                if line.startswith('###EXPECTED'):
                    test_input = False
                    continue
                
                if test_input:
                    self.test_yaml.append(line)
                else:
                    self.expected_result.append(line)

        self.test_yaml = ''.join(self.test_yaml)
        self.expected_result = ''.join(self.expected_result)
        if not self.expected_result:
            raise ValueError(f'Expected result is empty - missing "###EXPECTED" clause?')

    def test(self):
        from yamlfig.config import Config
        import yaml
        result = Config(self.test_yaml)
        expected = yaml.load(self.expected_result, Loader=yaml.Loader)
        self.assertEqual(result, expected)

    @classmethod
    def make_test_case_type(cls, test_file):
        def new_cls_init(obj, *args, **kwargs):
            YamlFileTest.__init__(obj, test_file, *args, **kwargs)

        test_type = type(cls.__name__ + '(' + os.path.splitext(os.path.basename(test_file))[0] + ')', (unittest.TestCase, ), { '__init__': new_cls_init, 'test': YamlFileTest.test })
        return test_type


_yaml_files_dir_rel = 'yaml_files'
_yaml_test_file_suffix = '_test.yaml'

curr_dir = os.path.abspath(os.path.dirname(__file__))
yaml_files_dir = os.path.join(curr_dir, _yaml_files_dir_rel)
for file in os.listdir(yaml_files_dir):
    if file.endswith(_yaml_test_file_suffix):
        full_path = os.path.join(yaml_files_dir, file)
        try:
            test_case_type = YamlFileTest.make_test_case_type(test_file=full_path)
            globals()[test_case_type.__name__] = test_case_type
        except Exception as e:
            print(f'Yaml test file {os.path.relpath(full_path, curr_dir)!r} will be ignored due to the following error: {e}')




# class YamlFilesTestSuite(unittest.TestSuite):
#     _yaml_files_dir_rel = 'yaml_files'
#     _yaml_test_file_suffix = '_test.yaml'

#     def __init__(self, tests, *args, **kwargs):
#         curr_dir = os.path.abspath(os.path.dirname(__file__))
#         yaml_files_dir = os.path.join(curr_dir, YamlFilesTestSuite._yaml_files_dir_rel)
#         for file in os.listdir(yaml_files_dir):
#             if file.endswith(YamlFilesTestSuite._yaml_test_file_suffix):
#                 full_path = os.path.join(yaml_files_dir, file)
#                 try:
#                     test_case = YamlFileTest.make_test(test_file=full_path)
#                     tests.addTest(test_case)
#                 except Exception as e:
#                     print(f'Yaml test file {os.path.relpath(full_path, curr_dir)!r} will be ignored due to the following error: {e}')

#         super().__init__(tests, *args, **kwargs)


# def load_tests(loader, stanndard_tests, pattern):
#     return YamlFilesTestSuite(stanndard_tests)


if __name__ == '__main__':
    unittest.main()
