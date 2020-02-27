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
        super().__init__(name, bases, dict)
        cls._bases = bases
        cls._dict = dict

    def __call__(cls, value, **kwargs):
        if cls is not ConfigScalar:
            return super().__call__(value, **kwargs)

        type_only = False
        if isinstance(value, type):
            value_type = value
            type_only = True
        else:
            value_type = type(value)

        if not issubclass(value_type, ConfigScalarMarker):
            #if value_type not in cls._allowed_scalar_types:
            #    raise ValueError(f'Unsupported scalar type: {value_type}')
            typename = f'ConfigScalar({value_type.__name__})'
            if value_type not in cls._types:
                #bt = cls._allowed_scalar_types[value_type]
                bt = cls._allowed_scalar_types.get(value_type, value_type)
                new_value_type = ConfigScalarMeta(typename, cls._bases + (bt, ), { **cls._dict, '_dyn_base': bt } )
                cls._types[value_type] = new_value_type
                value_type = new_value_type
            else:
                value_type = cls._types[value_type]

        if type_only:
            return value_type
        return ConfigNodeMeta.__call__(value_type, value, **kwargs)

    def __instancecheck__(cls, obj):
        if cls is ConfigScalar:
            return isinstance(obj, ConfigScalarMarker)
        else:
            return super().__instancecheck__(obj)

    def __subclasscheck__(cls, subcls):
        if cls is ConfigScalar:
            return issubclass(subcls, ConfigScalarMarker)
        else:
            return super().__subclasscheck__(subcls)

    def __repr__(cls):
        clsname = '.'.join(filter(bool, [cls.__module__, cls.__name__]))
        return f'<class {clsname!r}>'


class ConfigScalarMarker(ConfigNode):
    pass


class ConfigScalar(ConfigScalarMarker, metaclass=ConfigScalarMeta):
    def __new__(cls, value, **kwargs):
        return cls._dyn_base.__new__(cls, value)

    def __init__(self, value, **kwargs):
        ConfigNode.__init__(self, **kwargs)
        try:
            self._dyn_base.__init__(self, value, **kwargs)
        except:
            try:
                self._dyn_base.__init__(self, value)
            except:
                self._dyn_base.__init__(self)

    def __repr__(self, simple=False):
        if simple:
            t_prefix = ''
            if type(self) is not ConfigScalar(self._dyn_base):
                t_prefix = type(self).__name__ + '('
            return t_prefix + self._dyn_base.__repr__(self) + (')' if t_prefix else '')

        node = ConfigNode.__repr__(self)
        return node + '(' + self._dyn_base.__repr__(self) + ')'

    def __str__(self):
        return self._dyn_base.__str__(self)

    def _get_value(self):
        if self._dyn_base in [configbool, ConfigNone]:
            return self._dyn_base.get(self)

        return self

    def _set_value(self, other):
        raise RuntimeError(f'Cannot set value of an immutable config node: {self!r}')

    @namespace('yamlfigns')
    def named_nodes(self, prefix='', recurse=True, include_self=True, allow_duplicates=True):
        if include_self:
            yield prefix, self

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        if self._dyn_base in [configbool, ConfigNone]:
            return self._get_value()

        return self._dyn_base(self)
