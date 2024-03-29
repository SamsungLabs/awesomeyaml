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
import os
import re
import traceback
from pathlib import Path
from contextlib import ExitStack

from .utils import setUpModule, AssertRaisesChainedContext

from awesomeyaml.utils import import_name
from awesomeyaml.errors import ParsingError, PreprocessError, PremergeError, MergeError, EvalError, UnsafeError




class YamlFileTest():
    def __init__(self, test_file, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

        self.test_file = test_file
        self.test_yaml = []
        self.expected_result = []
        self.validate_code = []
        self.expected_error = []
        stage = 'test_yaml'

        with open(self.test_file, 'r') as test:
            for line in test:
                if line.startswith('###ERROR'):
                    stage = 'error'
                    continue
                if line.startswith('###EXPECTED'):
                    stage = 'expected'
                    continue
                if line.startswith('###VALIDATE'):
                    stage = 'validate'
                    continue

                if stage == 'test_yaml':
                    self.test_yaml.append(line)
                elif stage == 'validate':
                    self.validate_code.append(line)
                elif stage == 'error':
                    self.expected_error.append(line)
                elif stage == 'expected':
                    self.expected_result.append(line)
                else:
                    raise ValueError(f'Unexpected stage value! {stage!r}')


        if not self.test_yaml:
            raise ValueError('Empty yaml workload!')

        self.test_yaml = ''.join(self.test_yaml)
        self.expected_result = ''.join(self.expected_result)
        self.validate_code = ''.join(self.validate_code)
        if self.expected_error:
            self.expected_error_msg = ''.join(self.expected_error[1:]).strip()
            self.expected_error = self.expected_error[0].strip()

        if self.expected_error:
            if self.expected_result or self.validate_code:
                raise ValueError('###ERROR is mutually exclusive any other checks!')

    def test(self):
        from awesomeyaml.config import Config
        import yaml

        with ExitStack() as stack:
            if self.expected_error:
                assert not self.expected_result and not self.validate_code
                if self.expected_error in globals():
                    exc_type = globals()[self.expected_error]
                else:
                    exc_type = import_name(self.expected_error)
                exp_msg = self.expected_error_msg
                if not exp_msg:
                    exp_msg = None
                stack.enter_context(AssertRaisesChainedContext(exc_type, self, exp_msg))

            result = Config.build(self.test_yaml, filename=self.test_file)

            if not self.expected_error:
                if self.expected_result and self.expected_result != 'skip':
                    expected = yaml.load(self.expected_result, Loader=yaml.Loader)
                    self.assertEqual(result, expected)
                if self.validate_code:
                    exec(self.validate_code)

    @classmethod
    def make_test_case_type(cls, test_file, class_arg):
        def new_cls_init(obj, *args, **kwargs):
            YamlFileTest.__init__(obj, test_file, *args, **kwargs)

        test_type = type(cls.__name__ + '(' + class_arg + ')', (unittest.TestCase, ), { '__init__': new_cls_init, 'test': YamlFileTest.test })
        return test_type


_yaml_files_dir_rel = 'yaml_files'
_yaml_test_file_suffix = '_test.yaml'

curr_dir = Path(__file__).parent
yaml_files_dir = curr_dir.joinpath(_yaml_files_dir_rel)
for file in yaml_files_dir.glob("**/*" + _yaml_test_file_suffix):
    class_arg = str(file.relative_to(yaml_files_dir).with_suffix('')).replace(os.path.sep, '__')
    try:
        test_case_type = YamlFileTest.make_test_case_type(test_file=str(file), class_arg=class_arg)
        globals()[test_case_type.__name__] = test_case_type
        del test_case_type
    except Exception as e:
        full_path = str(file.absolute())
        print(f'Yaml test file {os.path.relpath(full_path, curr_dir)!r} will be ignored due to the following error: {e}')


if __name__ == '__main__':
    unittest.main()
