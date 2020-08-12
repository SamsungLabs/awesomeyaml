from .dict import ConfigDict
from ..namespace import namespace, staticproperty
from ..utils import import_name


class FunctionNode(ConfigDict):
    def __init__(self, func, args=None, **kwargs):
        ''' Func can be either str naming a function, or a pair (name, args) in which case args should be None
        '''
        if not isinstance(func, str):
            if isinstance(func, tuple):
                if args is not None:
                    raise ValueError('"args" passed directly and together with "func" resulting in an ambiguous assignment')
                self._func, args = func
            else:
                self._func = func
        else:
            self._func = func

        if args is not None and not isinstance(args, dict):
            if isinstance(args, list) or isinstance(args, tuple):
                args = { idx: val for idx, val in enumerate(args) }
            else:
                args = { 0: args }

        if not kwargs.get('delete', None):
            kwargs.setdefault('delete', True)
        super().__init__(args, **kwargs)
        self._default_delete = True

    def __bool__(self):
        return bool(self._func)

    @namespace('yamlfigns')
    def merge(self, other):
        if isinstance(other, str):
            self._func = other
            self.clear()
            return self

        if isinstance(other, FunctionNode) and type(self) != type(other):
            raise TypeError('Conflicting FunctionNode subclasses')

        try:
            self._func = other._func
        except AttributeError:
            pass

        return super().yamlfigns.merge(other)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        raise NotImplementedError()

    @namespace('yamlfigns')
    def represent(self):
        return self.yamlfigns.tag, self.yamlfigns.get_node_info(), super()._get_value()

    @namespace('yamlfigns')
    @property
    def func(self):
        return self._func

    def _get_value(self):
        return (self._func, super()._get_value())

    def _get_native_value(self):
        return (self._func, super()._get_native_value())

    def _set_value(self, value):
        self._func, super_val = value
        return super()._set_value(super_val)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def is_leaf():
       return False

    @namespace('yamlfigns')
    @property
    def tag(self):
        raise NotImplementedError()

    @staticmethod
    def _resolve_args(func, args):
        positional_args = { key: value for key, value in args.items() if isinstance(key, int) }
        if not positional_args:
            return [], {}, args

        keyword_args = { key: value for key, value in args.items() if isinstance(key, str) }
        assert len(positional_args) + len(keyword_args) == len(args)

        import inspect
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        idx_to_name = []
        for p in params:
            if p.kind == inspect.Parameter.VAR_POSITIONAL:
                break
            idx_to_name.append(p.name)

        idx = 0
        unpack = []
        while True:
            if idx not in positional_args:
                break
            unpack.append(positional_args.pop(idx))
            idx += 1

        kw_positional_args = {}
        for idx, value in positional_args.items():
            if idx >= len(idx_to_name):
                raise ValueError(f'Cannot resolve argument at position {idx} for function: {func} with signature {sig}')
            kw_positional_args[idx_to_name[idx]] = value

        return unpack, kw_positional_args, keyword_args
