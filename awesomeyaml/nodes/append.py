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

from .list import ConfigList
from ..namespace import namespace, staticproperty

from collections.abc import Sequence


class AppendNode(ConfigList):
    ''' A class implementing ``!append`` node.

        The append tag creates a list node which appends its
        content to another list on merge, instead of overwriting it.

        Supported syntax::

            !append [list]

        Merge behaviour:

            ==================  =================================
            Case                Behaviour
            ==================  =================================
            ``A <- Append``     ``return A.extend(Append)``
            ``None <- Append``  ``raise KeyError``
            otherwise           behaves as :py:class:`ConfigList`
            ==================  =================================

    '''
    def __init__(self, value, **kwargs):
        if not isinstance(value, Sequence) or isinstance(value, str) or isinstance(value, bytes):
            value = [value]
        super().__init__(value, **kwargs)

    @namespace('ayns')
    def on_premerge_impl(self, path, into):
        if into is None:
            return ConfigList(self)

        node = into.ayns.remove_node(path)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?)')
        node.extend(self)
        return node

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!append'
