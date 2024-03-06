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


class ExtendNode(ConfigList):
    ''' A class implementing ``!extend`` node.

        The extend tag behaves very similar to the !append tag
        but does not raises errors if the target list does not
        exist and/or is not a list.

        Supported syntax::

            !extend [list]

        Merge behaviour:

            ==================  =================================
            Case                Behaviour
            ==================  =================================
            ``A <- Append``     ``return A.extend(Append)`` iff
                                A.extend can be called
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

        try:
            node = into.ayns.get_node(path)
        except KeyError:
            return ConfigList(self)

        if hasattr(node, 'extend'):
            node.extend(self)
            into.ayns.remove_node(path)
            return node

        return ConfigList(self)

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!extend'
