from .composed import ComposedNode
from ..namespace import namespace
from ..utils import Bunch


class ConfigDict(ComposedNode, dict):
    def __init__(self, value=None, **kwargs):
        value = value if value is not None else {}
        ComposedNode.maybe_inherit_flags(value, kwargs)
        ComposedNode.__init__(self, children=value, **kwargs)
        dict.__init__(self, self._children)

    def _set(self, name, value):
        if name in dir(type(self)):
            raise ValueError(f'Cannot add a child node with name {name!r} as it would shadow a class method/attribute: {getattr(type(self), name)}')
        value = ComposedNode.yamlfigns.set_child(self, name, value)
        dict.__setitem__(self, name, value)
        return value

    def _del(self, name):
        ret = ComposedNode.yamlfigns.remove_child(self, name)
        dict.__delitem__(self, name)
        return ret

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return ComposedNode.__setattr__(self, name, value)

        return self._set(name, value)

    def __getattr__(self, name):
        if not ComposedNode.yamlfigns.has_child(self, name):
            raise AttributeError(f'Object {type(self).__name__!r} does not have attribute {name!r}')

        return ComposedNode.yamlfigns.get_child(self, name)

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
        return self.yamlfigns.has_child(name) # pylint: disable=no-value-for-parameter

    @namespace('yamlfigns')
    def set_child(self, name, value):
        self._set(name, value)

    @namespace('yamlfigns')
    def remove_child(self, name):
        return self._del(name)

    def clear(self):
        ComposedNode.yamlfigns.clear(self)
        dict.clear(self)

    def setdefault(self, key, value):
        if key not in self:
            return self._set(key, value)
        return self[key]

    def pop(self, k, *d):
        val = dict.pop(self, k, *d)
        if self.yamlfigns.has_child(k): # pylint: disable=no-value-for-parameter
            ComposedNode.yamlfigns.remove_child(self, k)
        return val

    def popitem(self, k, d=None):
        val = dict.popitem(self, k, d=d)
        if self.has_child(k):
            ComposedNode.yamlfigns.remove_child(self, k)
            #val.set_parent(None, None)
        return val

    @namespace('yamlfigns')
    def merge(self, other):
        if not isinstance(other, dict):
            raise TypeError('Dict expected')

        return super().yamlfigns.merge(other)

    @namespace('yamlfigns')
    def on_evaluate(self, path, root):
        return Bunch(self)

    def __repr__(self, simple=False):
        dict_repr = '{' + ', '.join([f'{n!r}: {c.__repr__(simple=True)}' for n, c in self.yamlfigns.named_children()]) + '}' # pylint: disable=no-value-for-parameter
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

    def _set_value(self, other):
        self.clear()
        for name, child in other.items():
            self.yamlfigns.set_child(name, child) # pylint: disable=no-value-for-parameter
