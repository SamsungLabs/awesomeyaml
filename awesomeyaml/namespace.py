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

class Namespace():
    def __init__(self, cls, name, names):
        self._cls = cls
        self._name = name
        self._names = names

    def __repr__(self):
        return f'<Namespace {self._cls.__name__}.{self._name} with type {type(self).__name__!r} at 0x{id(self):02x}>'

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        return Namespace.Bind(self, inst)

    def __set__(self, inst, value):
        raise AttributeError("can't set namespace")

    def __delete__(self, inst):
        raise AttributeError("can't delete namespace")

    def _resolve_endpoint(self, name):
        for cls in self._cls.__mro__:
            namespace = cls.__dict__.get(self._name, None)
            if namespace is None or not isinstance(namespace, Namespace):
                continue

            if name in namespace._names:
                return namespace._names[name]

        raise AttributeError(f'{self!r} does not have attribute {name!r}')

    def __getattr__(self, name):
        endpoint = self._resolve_endpoint(name)
        return endpoint.__get__(None, self._cls)

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            raise AttributeError("Can't set a new public attribute to a namespace")

        return super().__setattr__(name, value)

class BoundNamespace(Namespace):
    def __init__(self, namespace, inst):
        super().__init__(namespace._cls, namespace._name, namespace._names)
        self._orig_namespace = namespace
        self._inst = inst

    def __repr__(self):
        return f'<Bound namespace {self._cls.__name__}.{self._name} with type {type(self._orig_namespace).__name__!r} of {self._inst!r}>'

    def __getattr__(self, name):
        endpoint = self._resolve_endpoint(name)
        return endpoint.__get__(self._inst, type(self._inst))

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            error = False
            try:
                endpoint = self._resolve_endpoint(value)
            except AttributeError:
                error = True

            if not error:
                return endpoint.__set__(self._inst, value)

        return super().__setattr__(name, value)

Namespace.Bind = BoundNamespace


class staticproperty(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        if fget is not None and not isinstance(fget, staticmethod):
            raise ValueError('fget should be a staticmethod')
        if fset is not None and not isinstance(fset, staticmethod):
            raise ValueError('fset should be a staticmethod')
        if fdel is not None and not isinstance(fdel, staticmethod):
            raise ValueError('fdel should be a staticmethod')
        super().__init__(fget, fset, fdel, doc)

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget.__get__(inst, cls)() # pylint: disable=no-member

    def __set__(self, inst, val):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        return self.fset.__get__(inst)(val) # pylint: disable=no-member

    def __delete__(self, inst):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        return self.fdel.__get__(inst)() # pylint: disable=no-member


class namespaceable_property(property):
    def __init__(self, fget, fset, fdel, doc, namespace_data):
        super().__init__(fget, fset, fdel, doc)
        self._awesomeyaml_namespace = namespace_data

    def getter(self, func):
        return type(self)(func, self.fset, self.fdel, self.__doc__, self._awesomeyaml_namespace)

    def setter(self, func):
        return type(self)(self.fget, func, self.fdel, self.__doc__, self._awesomeyaml_namespace)

    def deleter(self, func):
        return type(self)(self.fget, self.fset, func, self.__doc__, self._awesomeyaml_namespace)


def namespace(namespace_name, namespace_type=Namespace):
    if not isinstance(namespace_name, str) or not namespace_name:
        raise ValueError(f'Namespace name should be a non-empty str, got: {namespace_name}')
    def namespace_decorator(func):
        namespace_data = (namespace_name, namespace_type)
        if isinstance(func, property) and not isinstance(func, namespaceable_property):
            func = namespaceable_property(func.__get__, func.__set__, func.__delete__, func.__doc__, namespace_data)
        else:
            func._awesomeyaml_namespace = namespace_data
        return func
    return namespace_decorator


class NamespaceableMeta(type):
    def __init__(cls, clsname, clsbases, clsnamespace, **kwargs):
        namespaces = {}
        for name, value in clsnamespace.items():
            if isinstance(value, type) and issubclass(value, Namespace):
                if len(value.__bases__) != 1:
                    raise ValueError('Expected exactly one base for an embedded Namespace type')
                namespace_name = name
                namespace_type = value.__bases__[0]
            elif hasattr(value, '_awesomeyaml_namespace'):
                namespace_name, namespace_type = value._awesomeyaml_namespace
            else:
                continue

            if name.startswith('__'):
                raise ValueError(f'Private entities (with names starting with "__") cannot be put in a namespace, when processing namespace attribute for entity: {value}, with name: {name!r}')
            if namespace_name in clsnamespace and not (isinstance(clsnamespace[namespace_name], type) and issubclass(clsnamespace[namespace_name], Namespace)):
                raise ValueError(f'Cannot hide a class member {name!r} under a namespace {namespace_name!r} as the namespace name {namespace_name!r} is already in use by {clsnamespace[namespace_name]}')
            if namespace_name in namespaces and namespaces[namespace_name][None] is not namespace_type:
                raise ValueError(f'Namespace {namespace_name!r} has inconsistent type: currently requested {namespace_type}, previously: {namespaces[namespace_name][None]}')

            namespace_names = namespaces.setdefault(namespace_name, { None: namespace_type })
            if isinstance(value, type):
                for subname, subvalue in value.__dict__.items():
                    namespace_names[subname] = subvalue
            else:
                namespace_names[name] = value

        for namespace_name, namespace_values in namespaces.items():
            namespace_type = namespace_values.pop(None)
            setattr(cls, namespace_name, namespace_type(cls, namespace_name, namespace_values))
            for name, value in namespace_values.items():
                # we need to take care of fields like '__module__'
                if name is not None and name in cls.__dict__ and not name.startswith('__'):
                    delattr(cls, name)


class Namespaceable(metaclass=NamespaceableMeta):
    pass
