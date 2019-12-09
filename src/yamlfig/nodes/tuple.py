from .composed import ComposedNode
from ..namespace import namespace


class ConfigTuple(ComposedNode, tuple):
    def __new__(cls, value):
        from .node import ConfigNode
        return tuple.__new__(cls, tuple(ConfigNode(child) for child in value))

    def __init__(self, value, **kwargs):
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

    @namespace('node_info')
    def set_child(self, index, value):
        raise TypeError('tuple does not support item assignment')

    @namespace('node_info')
    def remove_child(self, index):
        raise TypeError('tuple does not support item deletion')

    @namespace('node_info')
    def get_child(self, index, default=None):
        return self._get(index, default=default, raise_ex=False)

    def __contains__(self, value):
        return tuple.__contains__(self, value)

    def _get_child_accessor(self, childname, myname=''):
        if not myname:
            return childname
        return f'[{childname}]'

    def __repr__(self, simple=False):
        tuple_repr = '(' + ', '.join([c.__repr__(simple=True) for c in self.children()]) + ')'
        if simple:
            return tuple_repr

        node = ComposedNode.__repr__(self)
        return node + ': ' + tuple_repr

    def _get_value(self):
        return self

    def _set_value(self, other):
        raise TypeError(f'Cannot set value of an immutable config node: {self!r}')
