from .composed import ComposedNode
from ..namespace import namespace


class ConfigDict(ComposedNode, dict):
    def __init__(self, value=None, **kwargs):
        value = value or {}
        ComposedNode.__init__(self, children=value, **kwargs)
        dict.__init__(self, self._children)

    def _set(self, name, value):
        if name in dir(type(self)):
            raise ValueError(f'Cannot add a child node with name {name!r} as it would shadow a class method/attribute: {getattr(type(self), name)}')
        value = ComposedNode.node_info.set_child(self, name, value)
        dict.__setitem__(self, name, value)
        return value

    def _del(self, name):
        ComposedNode.node_info.remove_child(self, name)
        dict.__delitem__(self, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return ComposedNode.__setattr__(self, name, value)

        return self._set(name, value)

    def __getattr__(self, name):
        if not ComposedNode.node_info.has_child(self, name):
            raise AttributeError(f'Object {type(self).__name__!r} does not have attribute {name!r}')

        return ComposedNode.node_info.get_child(self, name)

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
        return self.node_info.has_child(name)

    @namespace('node_info')
    def set_child(self, name, value):
        self._set(name, value)

    @namespace('node_info')
    def remove_child(self, name):
        self._del(name)

    def clear(self):
        ComposedNode.node_info.clear(self)
        dict.clear(self)

    def setdefault(self, key, value):
        if key not in self:
            return self._set(key, value)
        return self[key]

    def pop(self, k, *d):
        val = dict.pop(self, k, *d)
        if self.node_info.has_child(k):
            ComposedNode.node_info.remove_child(self, k)
        return val

    def popitem(self, k, d=None):
        val = dict.popitem(self, k, d=d)
        if self.has_child(k):
            ComposedNode.node_info.remove_child(self, k)
            #val.set_parent(None, None)
        return val

    def merge(self, other):
        ''' Merge `other` into `self`.
            Args:
                `other` - a `yamlfig.Config` object
            Returns:
                `self` after updating
            Exceptions:
                The operation is considered atomic, i.e. if at any point during
                merging an unhandled exceptions is raised, `self` is unaffected.
        '''
        if other.node_info.delete:
            def maybe_keep(node, path):
                other_node = other.node_info.get_first_not_missing_node(path)
                return node.node_info.has_priority_over(other_node)

            self.node_info.filter_nodes(maybe_keep)

        for key, value in other.items():
            child = self.get(key, None)
            if child is None:
                self.node_info.set_child(key, value)
            else:
                if not child.node_info.is_leaf and type(child) == type(value):
                    child.merge(value)
                    if not child and not child.node_info.has_priority_over(value):
                        self.node_info.remove_child(key)
                else:
                    if value.node_info.has_priority_over(child, if_equal=True):
                        if not value and value.node_info.delete:
                            self.node_info.remove_child(key)
                        else:
                            self.node_info.set_child(key, value)


    def __repr__(self, simple=False):
        dict_repr = '{' + ', '.join([f'{n!r}: {c.__repr__(simple=True)}' for n, c in self.node_info.named_children()]) + '}'
        if simple:
            return dict_repr

        node = ComposedNode.__repr__(self)
        return node + ': ' + dict_repr

    def __str__(self):
        def strify(kv):
            k, v = kv
            return str(k) + ': ' + str(v)

        return '{' + ', '.join(map(strify, self.items())) + '}'

    def _get_value(self):
        return self

    def _set_value(self, other):
        self.clear()
        for name, child in other.items():
            self.node_info.set_child(name, child)
