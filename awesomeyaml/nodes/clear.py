# Copyright 2022-2023 Samsung Electronics Co., Ltd.
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


class ClearNode(ConfigNode):
    def __init__(self, value, *args, **kwargs):
        if value is not None:
            raise ValueError(f'!clear does not expect any arguments, but got: {value!r}')

        super().__init__(*args, **kwargs)

    @namespace('ayns')
    def on_premerge_impl(self, path, into):
        node = into.ayns.get_node(path)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?)')
        node.clear()
        return node

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!clear'
