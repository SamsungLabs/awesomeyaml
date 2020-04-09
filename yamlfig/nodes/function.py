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
