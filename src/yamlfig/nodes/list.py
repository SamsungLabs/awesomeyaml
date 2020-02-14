from .composed import ComposedNode
from ..namespace import namespace, staticproperty


class ConfigList(ComposedNode, list):
    def __init__(self, value=None, **kwargs):
        value = value if value is not None else []
        ComposedNode.maybe_inherit_flags(value, kwargs)
        ComposedNode.__init__(self, children={ i: v for i, v in enumerate(value) }, **kwargs)
        list.__init__(self, self._children.values())

    def _validate_index(self, index):
        if not isinstance(index, int):
            raise TypeError(f'Index should be integer, got: {type(index)}')
        if abs(index) >= len(self):
            raise IndexError('List index out of range')
        if index < 0:
            index = len(self) + index

        return index

    def _set(self, index, value):
        index = self._validate_index(index)
        try:
            value = ComposedNode.yamlfigns.set_child(self, index, value)
            list.__setitem__(self, index, value)
        except:
            ComposedNode.yamlfigns.remove_child(self, index)
            raise

    def _del(self, index):
        index = self._validate_index(index)
        for i in range(index+1, len(self)):
            self[i-1] = self[i]

        ret = ComposedNode.yamlfigns.remove_child(self, len(self) - 1)
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

    @namespace('yamlfigns')
    def set_child(self, index, value):
        return self._set(index, value)

    @namespace('yamlfigns')
    def remove_child(self, index):
        return self._del(index)

    @namespace('yamlfigns')
    def get_child(self, index, default=None):
        return self._get(index, default=default, raise_ex=False)

    def __contains__(self, value):
        return list.__contains__(self, value)

    def append(self, value):
        value = ComposedNode.yamlfigns.set_child(self, len(self), value)
        list.append(self, value)

    def remove(self, value):
        self._del(self.index(value))

    def clear(self):
        ComposedNode.yamlfigns.clear(self)
        list.clear(self)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def is_leaf():
        return False

    def __repr__(self, simple=False):
        list_repr = '[' + ', '.join([c.__repr__(simple=True) for c in self.yamlfigns.children()]) + ']'
        if simple:
            return type(self).__name__ + list_repr

        node = ComposedNode.__repr__(self)
        return node + list_repr

    def __str__(self):
        return type(self).__name__ + '[' + ', '.join(map(str, self)) + ']'

    def _get_value(self):
        return self

    def _set_value(self, other):
        self.clear()
        for index, child in enumerate(other):
            self.set_child(index, child)
