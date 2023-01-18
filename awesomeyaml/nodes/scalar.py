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
        if value is not None:
            raise ValueError(f'!null does not expect any arguments, but got: {value!r}')
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
    _rev_scalar_types = { value: key for key, value in _allowed_scalar_types.items() }
    _types = {}

    def __init__(cls, name, bases, dict, **kwargs):
        super().__init__(name, bases, dict, **kwargs)
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

        if value_type not in ConfigScalarMeta._allowed_scalar_types and value_type in ConfigScalarMeta._rev_scalar_types:
            value_type = ConfigScalarMeta._rev_scalar_types[value_type]

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
        ret = ConfigNodeMeta.__call__(value_type, value, **kwargs)
        return ret

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
    def __new__(cls, *value, **kwargs):
        return cls._dyn_base.__new__(cls, *value) # pylint: disable=no-member

    def __init__(self, value, **kwargs):
        ConfigNode.__init__(self, **kwargs)
        try:
            self._dyn_base.__init__(self, value, **kwargs)
        except:
            try:
                self._dyn_base.__init__(self, value)
            except:
                self._dyn_base.__init__(self) # pylint: disable=no-member

    def __repr__(self, simple=False):
        if simple:
            t_prefix = ''
            if type(self) is not ConfigScalar(self._dyn_base): # pylint: disable=no-member
                t_prefix = type(self).__name__ + '('
            return t_prefix + self._dyn_base.__repr__(self) + (')' if t_prefix else '') # pylint: disable=no-member

        node = ConfigNode.__repr__(self)
        return node + '(' + self._dyn_base.__repr__(self) + ')' # pylint: disable=no-member

    def __str__(self):
        if self._dyn_base is str:
            return str.__str__(self)

        if self._dyn_base is ConfigNone:
            return ConfigNone.__str__(self)

        return str(self._dyn_base(self)) # pylint: disable=no-member

    def _get_value(self):
        if self._dyn_base in [configbool, ConfigNone]: # pylint: disable=no-member
            return self._dyn_base.get(self) # pylint: disable=no-member

        return self

    def _set_value(self, other):
        raise RuntimeError(f'Cannot set value of an immutable config node: {self!r}')

    @namespace('ayns')
    def named_nodes(self, prefix='', recursive=True, include_self=True, allow_duplicates=True):
        if include_self:
            yield prefix, self

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        return self._get_native_value()

    def _get_native_value(self):
        if self._dyn_base in [configbool, ConfigNone]: # pylint: disable=no-member
            return self._get_value()

        return self._dyn_base(self) # pylint: disable=no-member

    def _is_primary_type_dynamic(self):
        return type(self).__mro__[0] in ConfigScalar._types.values()

    def __reduce__(self):
        if not self._is_primary_type_dynamic():
            return object.__reduce__(self)

        state = self.__dict__.copy()
        return ConfigScalar, (self._get_native_value(), ), state # pylint: disable=no-member

    # def __eq__(self, other):
    #     if isinstance(other, ConfigScalar):
    #         other = other._get_native_value()
    #     return self._get_native_value() == other

    # def __hash__(self):
    #     return self._get_native_value().__hash__()
