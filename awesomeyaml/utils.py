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

import sys


class persistent_id(int):
    ''' The purpose of this class is to replace built-in ``id`` function
        in cases when keeping an id of an object should prolong the object's
        life, mostly to ensure that the returned id will be unique within a certain
        scope (to provide an easy way of identifying objects).
        This class is a simple extension of the `int` class which additionally
        to the normal value holds a reference to the object whose id it holds,
        therefore effectively preventing it from being deallocated and ensuring
        that the id will continue to uniquely identify that object.
        The downside of this approach is the fact that the objects will
        remain in memory for as long as its persistent_id is in use - therefore
        it should be used in cases when memory is not an issue and correctness of
        unique identification is preferred.
        
        An example use case could be having a cache (memo) of objects already
        processed, where the incoming objects are managed (created etc.) by a user,
        for example with a generator. The generator might but might not return the same
        object multiple times in which case we don't want to process it multiple times.
        Since we don't know in advance if an object will be given to us multiple times,
        we need to ensure that we can identify a situation when it happens as the objects arrive.
        A simple idea is to keep track of ids of objects which have already been processed in
        a cache/memo, using for example a set::

            def process_all(objs):
                memo = set()
                for obj in objs:
                    if id(obj) not in memo:
                        memo.add(id(obj))
                        yield process(obj)

        where ``process`` is potentially expensive processing of objects in ``objs``.
        However, if it is possible for an object to be deleted after processing (i.e. no one stores
        a reference to it) the id might be repeated easily but for a different object, creating
        a false impression that the object has already been processed, where in fact it was
        a different one which just happened to had the same id.
        The following code illustrates that::

            class MyObject():
                def __init__(self, value):
                    self.value = value

            def obj_gen(num_objs):
                for i in range(num_objs):
                    yield MyObject(i)

            def process(obj):
                # expensive computations
                return obj.value ** 2

            def process_all(objs):
                memo = set()
                for obj in objs:
                    if id(obj) not in memo:
                        memo.add(id(obj))
                        yield process(obj)

            processed = list(process_all(obj_gen(100)))
            assert len(processed) == 100

        When running the above code, it's possible that only a couple of first objects will be processed
        (in my case first 2) because later objects will be allocated at the place of previous ones which will
        trick the ``memo`` within ``process``. Therefore it's important to keep a reference to all objects
        whose ids are kept to ensure their uniqueness. A couple of different solutions could be used to
        address it, e.g.: instead of a set one could use dict and store pairs ``id(obj): obj`` within it;
        or simply precompute all objects ahead of execution and keep them in a separate container.
        Both approaches have very similar cost in terms of memory consumption  as the solution presented here
        (prevent all objects from being deallocated), but at the same time they have some additional drawbacks:

         - the approach with storing the original object in a set can add some hassle if a dict is already in use
           to store results of processing of the object, i.e.::

                def process_all(objs):
                    memo = {}
                    for obj in objs:
                        if id(obj) not in memo:
                            result = process(obj)
                            memo[id(obj)] = result
                        else:
                            result = memo[id(obj)]

                        yield result

           the solution would be to either store pairs ``id(obj): (obj, process(obj))`` or have two memos which in both cases pollutes the code;
         - the second solution requires precomputing all values ahead of time which will not work nicely when chaining generators.

        The proposed solution requires simply changing ``id`` to ``persistant_id`` which is clean and nice::

            class MyObject():
                def __init__(self, value):
                    self.value = value

            def obj_gen(num_objs):
                for i in range(num_objs):
                    yield MyObject(i)

            def process(obj):
                # expensive computations
                return obj.value ** 2

            def process_all(objs):
                memo = {}
                for obj in objs:
                    if id(obj) not in memo:
                        result = process(obj)
                        memo[persistent_id(obj)] = result
                    else:
                        result = memo[id(obj)]

                    yield result

            processed = list(process_all(obj_gen(100)))
            assert len(processed) == 100

    '''

    def __new__(cls, obj):
        return int.__new__(cls, id(obj))

    def __init__(self, obj):
        ''' Return id of the ``obj`` which holds a reference to it, ensuring that no other
            object will use the same id as long as the ``persistent_id`` object exists.
        '''
        self._ref = obj


def pad_with_none(*args, minlen=None):
    if minlen is None or len(args) >= minlen:
        return args
    return (*args, *([None] * (minlen - len(args))))


def import_name(symbol_name):
    if not symbol_name or symbol_name.endswith('.'):
        raise ValueError(f'Invalid target name: {symbol_name}')

    elements = symbol_name.split('.')
    current = None
    try_import = True
    exceptions = []

    def _build_import_exception(symbol, last, excs):
        flat_excs = []
        for e in excs:
            this_ex_chain = []
            while e is not None:
                this_ex_chain.insert(0, e)
                e = getattr(e, '__cause__', None)

            flat_excs.extend(this_ex_chain)

        ex = None
        for e in flat_excs:
            if ex is not None:
                e.__cause__ = ex
            ex = e

        if ex is not None:
            import traceback
            ex = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
        else:
            ex = '<No information>'

        return ImportError(f'Cannot find an entity named: {symbol!r}, last found element was: {last}, see exception(s) below for potential reasons what could have gone wrong:\n\n{ex}')

    for element in elements:
        if try_import:
            import importlib
            if current:
                try:
                    current = importlib.import_module('.' + element, package=current.__name__)
                    continue
                except ImportError as e:
                    exceptions.append(e)
                    try_import = False
            else:
                try:
                    current = importlib.import_module(element)
                    continue
                except ImportError as e:
                    exceptions.append(e)
                    try_import = False

        if current is not None:
            try:
                current = getattr(current, element)
                continue
            except AttributeError as e:
                exceptions.append(e)
                pass

        if current is None and len(elements) == 1:
            import builtins
            try:
                current = getattr(builtins, element)
                continue
            except AttributeError as e:
                exceptions.append(e)
                pass

        raise _build_import_exception(symbol_name, current, exceptions)

    return current


class Bunch(dict):
    def __init__(self, other=None):
        if other is None:
            other = {}
        super().__init__(other)

    def __getattr__(self, name):
        if name not in self:
            raise AttributeError(f'Object {type(self).__name__!r} does not have attribute {name!r}')
        return self[name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)

        if name in self.__dict__:
            raise ValueError('Name conflict!')

        self[name] = value

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            del self[name]


class LazyModule():
    def __init__(self, module):
        self.module = module

    def __getattr__(self, name):
        return getattr(self.module, name)


def add_module_properties(module_name, properties):
    module = sys.modules[module_name]
    replace = False
    if isinstance(module, LazyModule):
        lazy_type = type(module)
    else:
        lazy_type = type('LazyModule({})'.format(module_name), (LazyModule,), {})
        replace = True

    for name, prop in properties.items():
        setattr(lazy_type, name, prop)

    if replace:
        sys.modules[module_name] = lazy_type(module)


def python_is_at_least(major, minor):
    return sys.version_info[0] > major or (sys.version_info[0] == major and sys.version_info[1] >= minor)


def python_is_exactly(major, minor):
    return sys.version_info[0] == major and sys.version_info[1] == minor


def notnone_or(value, alt):
    if value is None:
        return alt
    return value
