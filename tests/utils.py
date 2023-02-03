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


import re
import traceback


def setUpModule():
    import os
    import sys
    new_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    sys.path = [new_path] + sys.path
    try:
        import awesomeyaml
    finally:
        sys.path = sys.path[1:]


def linear_f(x, *, a=1, b=0):
    return a*x + b


def cubic_f(x, *, a=1, b=0):
    return a*(x**3) + b


def square_f(x, a=1, b=0):
    return a*(x**2) + b


def dummy(*args, **kwargs):
    return (args, kwargs)


def malicious(*args, **kwargs):
    raise RuntimeError(f'Malicious function called! Args: {args}, {kwargs}')


class persistent_id(int):
    def __new__(self, obj):
        super().__new__(id(obj))

    def __init__(self, obj):
        self.obj = obj


class AssertRaisesChainedContext():
    def __init__(self, expected, test_case, expected_regex=None):
        self.test_case = test_case
        self.expected = expected
        if expected_regex is not None:
            expected_regex = re.compile(expected_regex)
        self.expected_regex = expected_regex
        self.msg = None

    def _raiseFailure(self, standardMsg):
        msg = self.test_case._formatMessage(self.msg, standardMsg)
        raise self.test_case.failureException(msg)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            self._raiseFailure("{} not raised".format(exc_name))
        else:
            traceback.clear_frames(tb)

        def _next():
            nonlocal exc_type, exc_value, tb
            exc_value = exc_value.__context__
            exc_type = type(exc_value)
            if exc_value is not None:
                tb = exc_value.__traceback__
            else:
                tb = None

        found = None
        match = False
        while exc_value is not None:
            if not issubclass(exc_type, self.expected):
                # let unexpected exceptions pass through
                _next()
                continue

            found = exc_value

            # store exception, without traceback, for later retrieval
            self.exception = exc_value.with_traceback(None)
            if self.expected_regex is None:
                break

            expected_regex = self.expected_regex
            if not expected_regex.search(str(exc_value)):
                _next()
                continue

            match = True
            break

        if found is None:
            return False

        if self.expected_regex is not None and not match:
            self._raiseFailure('"{}" does not match "{}"'.format(
                expected_regex.pattern, str(found)))

        return True
