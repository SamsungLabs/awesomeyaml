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
from ..namespace import namespace, staticproperty
from .. import utils
from ..errors import MergeError


class ConfigList(ComposedNode, list):
    _default_delete = True

    def __init__(self, value=None, **kwargs):
        value = value if value is not None else []
        ComposedNode.__init__(self, children={ i: v for i, v in enumerate(value) }, **kwargs)
        list.__init__(self, self._children.values())

    def _validate_index(self, index, strict=True):
        if not isinstance(index, int):
            raise TypeError(f'Index should be integer, got: {type(index)}')
        if (abs(index) > len(self) or index == len(self)) and strict:
            raise IndexError('List index out of range')
        if index < 0:
            index = len(self) + index

        return min(len(self), max(0, index))

    def _set(self, index, value, strict=True):
        index = self._validate_index(index, strict=strict)
        value = ComposedNode.ayns.set_child(self, index, value)
        try:
            if index == len(self):
                list.append(self, value)
            else:
                list.__setitem__(self, index, value)
        except:
            ComposedNode.ayns.remove_child(self, index)
            raise

    def _del(self, index):
        index = self._validate_index(index)
        for i in range(index+1, len(self)):
            self[i-1] = self[i]

        ret = ComposedNode.ayns.remove_child(self, len(self) - 1)
        list.__delitem__(self, -1)
        return ret

    def _get(self, index, default=None, raise_ex=True):
        try:
            index = self._validate_index(index)
        except (IndexError, TypeError):
            if raise_ex:
                raise
            return default

        return list.__getitem__(self, index)

    def __setitem__(self, index, value):
        return self._set(index, value)

    def __delitem__(self, index):
        self._del(index)

    def __getitem__(self, index):
        return self._get(index, raise_ex=True)

    @namespace('ayns')
    def set_child(self, index, value):
        return self._set(index, value, strict=False)

    @namespace('ayns')
    def remove_child(self, index):
        return self._del(index)

    @namespace('ayns')
    def get_child(self, index, default=None):
        return self._get(index, default=default, raise_ex=False)

    def __contains__(self, value):
        return list.__contains__(self, value)

    def append(self, value):
        value = ComposedNode.ayns.set_child(self, len(self), value)
        list.append(self, value)

    def remove(self, value):
        self._del(self.index(value))

    def clear(self):
        ComposedNode.ayns.clear(self)
        list.clear(self)

    def extend(self, other):
        for val in other:
            self.append(val)

    def insert(self, index, value):
        index = self._validate_index(index, strict=False)
        self._children = { ((idx+1) if idx >= index else idx): value for idx, value in self._children.items() }
        value = ComposedNode.ayns.set_child(self, index, value)
        list.insert(self, index, value)

    if not utils.python_is_at_least(3, 7):
        # for python < 3.7 (i.e., 3.6 and older)
        # list subclasses are unpickled without calling
        # custom 'append' and/or 'extend' and rather
        # using "the fastest" possible option which is to
        # populate the built-in function type alone
        # (see: https://stackoverflow.com/questions/52333864/pickle-breaking-change-in-python-3-7)
        # Because of that we need to populate _children
        # of the composed node ourselves after the list has
        # been unpickled (which happens before __setstate__
        # is called).
        def __setstate__(self, state):
            super().__setstate__(state)
            assert not self._children
            self._children = { idx: child for idx, child in enumerate(self) }

    @namespace('ayns')
    def on_merge_impl(self, prefix, other):
        if isinstance(other, dict):
            _missing_keys = []
            for key in other.ayns.children_names():
                first_missing = None
                try:
                    self._validate_index(key, strict=True)
                except IndexError:
                    _missing_keys.append(key.ayns.native_value)
                    if first_missing is None:
                        first_missing = key
            if _missing_keys:
                raise MergeError(f'merging a dict into a list requires all dict nodes to map to the existing indices in the list but the following keys are invalid: {_missing_keys}', node=self, path=prefix, extra_node=first_missing)

        def keep_if_exists(path, node):
            if not node.ayns.delete:
                return True
            current = self.ayns.get_first_not_missing_node(path)
            return node.ayns.has_priority_over(current, if_equal=True)

        if isinstance(other, ComposedNode):
            other.ayns.filter_nodes(keep_if_exists)

        return super().ayns.on_merge_impl(prefix, other)

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        return list(ctx.evaluate_node(value, path+[key]) for key, value in self.ayns.named_children())

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def is_leaf():
        return False

    def __repr__(self, simple=False):
        list_repr = '[' + ', '.join([c.__repr__(simple=True) for c in self.ayns.children()]) + ']' # pylint: disable=no-value-for-parameter
        if simple:
            return type(self).__name__ + list_repr

        node = ComposedNode.__repr__(self)
        return node + list_repr

    def __str__(self):
        return type(self).__name__ + '[' + ', '.join(map(str, self)) + ']'

    def _get_value(self):
        return self

    def _get_native_value(self):
        return list(n.ayns.native_value for n in self)

    def _set_value(self, other):
        self.clear()
        for index, child in enumerate(other):
            self.set_child(index, child)
