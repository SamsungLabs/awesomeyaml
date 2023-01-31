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
from ..utils import Bunch


class ConfigDict(ComposedNode, dict):
    def __init__(self, value=None, **kwargs):
        value = value if value is not None else {}
        #ComposedNode.maybe_inherit_flags(value, kwargs)
        ComposedNode.__init__(self, children=value, **kwargs)
        dict.__init__(self, self._children)

    def _set(self, name, value):
        if name in dir(type(self)):
            raise ValueError(f'Cannot add a child node with name {name!r} as it would shadow a class method/attribute: {getattr(type(self), name)}')
        value = ComposedNode.ayns.set_child(self, name, value)
        dict.__setitem__(self, name, value)
        return value

    def _del(self, name):
        ret = ComposedNode.ayns.remove_child(self, name)
        dict.__delitem__(self, name)
        return ret

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return ComposedNode.__setattr__(self, name, value)

        return self._set(name, value)

    def __getattr__(self, name):
        if not ComposedNode.ayns.has_child(self, name):
            raise AttributeError(f'Object {type(self).__name__!r} does not have attribute {name!r}')

        return ComposedNode.ayns.get_child(self, name)

    def __delattr__(self, name):
        if name.startswith('_'):
            return ComposedNode.__delattr__(self, name)

        self._del(name)

    def __setitem__(self, name, value):
        if isinstance(name, str) and name.startswith('_'):
            return dict.__setitem__(self, name, value)

        return self._set(name, value)

    def __delitem__(self, name):
        if isinstance(name, str) and name.startswith('_'):
            return dict.__delitem__(self, name)

        self._del(name)

    def __contains__(self, name):
        return self.ayns.has_child(name) # pylint: disable=no-value-for-parameter

    @namespace('ayns')
    def set_child(self, name, value):
        self._set(name, value)

    @namespace('ayns')
    def remove_child(self, name):
        return self._del(name)

    def clear(self):
        ComposedNode.ayns.clear(self)
        dict.clear(self)

    def setdefault(self, key, value):
        if key not in self:
            return self._set(key, value)
        return self[key]

    def pop(self, k, *d):
        val = dict.pop(self, k, *d)
        if self.ayns.has_child(k): # pylint: disable=no-value-for-parameter
            ComposedNode.ayns.remove_child(self, k)
        return val

    def popitem(self, k, d=None):
        val = dict.popitem(self, k, d=d)
        if self.has_child(k):
            ComposedNode.ayns.remove_child(self, k)
            #val.set_parent(None, None)
        return val

    def update(self, other, **kwargs):
        try:
            itr = other.items()
        except:
            itr = iter(other)

        for k, v in itr:
            self._set(k, v)
        for k, v in kwargs.items():
            self._set(k, v)

    @namespace('ayns')
    def on_merge_impl(self, prefix, other):
        return super().ayns.on_merge_impl(prefix, other)

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        return Bunch((ctx.evaluate_node(key), ctx.evaluate_node(value, path+[key])) for key, value in self.ayns.named_children())

    def __repr__(self, simple=False):
        dict_repr = '{' + ', '.join([f'{n!r}: {c.__repr__(simple=True)}' for n, c in self.ayns.named_children()]) + '}' # pylint: disable=no-value-for-parameter
        if simple:
            return type(self).__name__ + dict_repr

        node = ComposedNode.__repr__(self)
        return node + dict_repr

    def __str__(self):
        def strify(kv):
            k, v = kv
            return repr(k) + ': ' + v.__repr__(simple=True)

        return type(self).__name__ + '{' + ', '.join(map(strify, self.items())) + '}'

    def _get_value(self):
        return self

    def _get_native_value(self):
        return dict((k.ayns.native_value,v.ayns.native_value) for k,v in self.items())

    def _set_value(self, other):
        self.clear()
        for name, child in other.items():
            self.ayns.set_child(name, child) # pylint: disable=no-value-for-parameter
