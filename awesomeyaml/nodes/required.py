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

from .node import ConfigNode
from ..namespace import namespace, staticproperty


class RequiredNode(ConfigNode):
    def __init__(self, value, *args, **kwargs):
        if value is not None:
            raise ValueError(f'!required does not expect any arguments, but got: {value!r}')

        super().__init__(*args, **kwargs)

    @namespace('ayns')
    def on_evaluate(self, path, ctx):
        raise ValueError(f'RequiredNode should not appear during evaluation: {path!r}')

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!required'

    @namespace('ayns')
    @property
    def value(self):
        return str()

    def __eq__(self, other):
        return isinstance(other, RequiredNode)
