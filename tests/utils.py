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
    raise RuntimeError('Malicious function called!')


class persistent_id(int):
    def __new__(self, obj):
        super().__new__(id(obj))

    def __init__(self, obj):
        self.obj = obj

