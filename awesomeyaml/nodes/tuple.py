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

from .composed import ComposedNode
from ..namespace import namespace

# TODO: finish implementation to make it conformant with other ComposedNode subtypes (i.e. add merge etc.)


class ConfigTuple(ComposedNode, tuple):
    def __new__(cls, value, **kwargs):
        from .node import ConfigNode
        value = value if value is not None else tuple()
        return tuple.__new__(cls, tuple(ConfigNode(child) for child in value))

    def __init__(self, value=None, **kwargs):
        value = value if value is not None else tuple()
        #ComposedNode.maybe_inherit_flags(value, kwargs)
        kwargs.setdefault('delete', True)
        ComposedNode.__init__(self, children={ i: v for i, v in enumerate(value) }, **kwargs)

    def _validate_index(self, index):
        if not isinstance(index, int):
            raise TypeError(f'Index should be integer, got: {type(index)}')
        if abs(index) >= len(self):
            raise IndexError('Tuple index out of range')
        if index < 0:
            index = len(self) + index

        return index

    def _get(self, index, default=None, raise_ex=True):
        try:
            index = self._validate_index(index)
        except (IndexError, TypeError):
            if raise_ex:
                raise
            return default

        return tuple.__getitem__(self, index)

    def __getitem__(self, index):
        return self._get(index, raise_ex=True)

    @namespace('ayns')
    def set_child(self, index, value):
        raise TypeError('tuple does not support item assignment')

    @namespace('ayns')
    def remove_child(self, index):
        raise TypeError('tuple does not support item deletion')

    @namespace('ayns')
    def get_child(self, index, default=None):
        return self._get(index, default=default, raise_ex=False)

    @namespace('ayns')
    def map_nodes(self, map_fn):
        raw = tuple(map(map_fn, self))
        return ConfigTuple(raw)

    def __contains__(self, value):
        return tuple.__contains__(self, value)

    def __repr__(self, simple=False):
        tuple_repr = '(' + ', '.join([c.__repr__(simple=True) for c in self.ayns.children()]) + ')' # pylint: disable=no-value-for-parameter
        if simple:
            return type(self).__name__ + tuple_repr

        node = ComposedNode.__repr__(self)
        return node + tuple_repr

    def __str__(self):
        return type(self).__name__ + '(' ', '.join(map(str, self)) + ')'

    def _get_value(self):
        return self

    def _set_value(self, other):
        raise TypeError(f'Cannot set value of an immutable config node: {self!r}')
