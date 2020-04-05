

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
    module_name, entity_name = pad_with_none(*symbol_name.rsplit('.', maxsplit=1), minlen=2)
    if not entity_name:
        if symbol_name.endswith('.'):
            raise ValueError(f'Invalid target name: {symbol_name}')
        entity_name = module_name
        module_name = None

    if module_name is None:
        if entity_name not in globals():
            import builtins
            if entity_name not in dir(builtins):
                import importlib
                try:
                    return importlib.import_module(entity_name)
                except ImportError as e:
                    raise ImportError(f'Cannot find an entity named {entity_name!r} in the global variables, the builtin module and cannot import it as a top-level module - error: {str(e)}')
            else:
                return getattr(builtins, entity_name)
        else:
            return globals()[entity_name]
    else:
        import importlib
        module = importlib.import_module(module_name)
        if entity_name not in dir(module):
            try:
                return importlib.import_module(module_name + '.' + entity_name)
            except ImportError:
                raise ImportError(f'Cannot find an entity named: {entity_name!r} in module: {module}')
        return getattr(module, entity_name)

    raise RuntimeError('Unreachable')


class Bunch(dict):
    def __init__(self, other):
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
