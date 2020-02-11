from .node import ConfigNode, ConfigNodeMeta
from ..namespace import namespace


class configbool(int):
    def __new__(cls, value):
        return int.__new__(cls, bool(value))

    def __repr__(self):
        return bool(self).__repr__()

    def __str__(self):
        return bool(self).__str__()

    def __eq__(self, other):
        return bool(self) == other

    def __neq__(self, other):
        return bool(self) != other

    def get(self):
        return bool(self)


class ConfigNone(object):
    def __new__(cls, value):
        assert value is None
        return object.__new__(cls)

    def __repr__(self):
        return repr(None)

    def __str__(self):
        return str(None)

    def __bool__(self):
        return False

    def __eq__(self, other):
        if other is None:
            return True
        return isinstance(other, ConfigNone)

    def get(self):
        return None


class ConfigScalarMeta(ConfigNodeMeta):
    _allowed_scalar_types = { int: int, float: float, bool: configbool, str: str, type(None): ConfigNone }
    _types = {}

    def __init__(cls, name, bases, dict):
        cls._bases = bases
        cls._dict = dict
        super().__init__(name, bases, dict)

    def __call__(cls, value, *args, **kwargs):
        if type(value) not in cls._allowed_scalar_types:
            raise ValueError(f'Unsupported scalar type: {type(value)}')
        typename = f'ConfigScalar({type(value).__name__})'
        t = cls._types.get(typename)
        if t is None:
            bt = cls._allowed_scalar_types[type(value)]
            t = ConfigScalarMeta(typename, cls._bases + (bt, ), { **cls._dict, '_dyn_base': bt } )
            cls._types[typename] = t

        obj = t.__new__(t, value)
        obj.__init__(value, *args, **kwargs)
        return obj


class ConfigScalar(ConfigNode, metaclass=ConfigScalarMeta):
    def __new__(cls, value):
        return cls._dyn_base.__new__(cls, value)

    def __init__(self, value, **kwargs):
        ConfigNode.__init__(self, **kwargs)

    def __repr__(self, simple=False):
        if simple:
            return self._dyn_base.__repr__(self)

        node = ConfigNode.__repr__(self)
        return node + ': ' + self._dyn_base.__repr__(self)

    def __str__(self):
        return self.__repr__(simple=True)

    def _get_value(self):
        if self._dyn_base in [configbool, ConfigNone]:
            return self._dyn_base.get(self)

        return self

    def _set_value(self, other):
        raise RuntimeError(f'Cannot set value of an immutable config node: {self!r}')

    @namespace('node_info')
    def named_nodes(self, prefix='', recurse=True, include_self=True, allow_duplicates=True):
        if include_self:
            yield prefix, self
