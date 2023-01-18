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

from .scalar import ConfigScalar
from ..namespace import namespace, staticproperty


class PrevNode(ConfigScalar(str)):
    def __init__(self, ref, **kwargs):
        super().__init__(ref)

    @namespace('ayns')
    def on_premerge_impl(self, path, into):
        node = into.ayns.remove_node(self)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?)')
        return node

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!prev'
