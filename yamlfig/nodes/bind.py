from .dict import ConfigDict
from ..namespace import namespace, staticproperty
from ..utils import import_name

from functools import partial


class BindNode(ConfigDict):
    def __init__(self, func, args=None, **kwargs):
        ''' Func can be either str naming a function, or a pair (name, args) in which canse args should be None
        '''
        if not isinstance(func, str):
            if isinstance(func, tuple):
                if args is not None:
                    raise ValueError('"args" passed directly and toghether with "func" resulting in an ambiguous assignment')
                self._func, args = func
        else:
            self._func = func

        kwargs.setdefault('delete', True)
        super().__init__(args, **kwargs)

    def __bool__(self):
        return bool(self._func)

    @namespace('yamlfigns')
    def merge(self, other):
        if isinstance(other, str):
            self._func = other
            self.clear()
            return self

        try:
            self._func = other._func
        except AttributeError:
            pass

        return super().yamlfigns.merge(other)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        self._func = import_name(self._func)
        return partial(self._func, **self)

    @namespace('yamlfigns')
    @property
    def func(self):
        return self._func

    def _get_value(self):
        return (self._func, super()._get_value())

    def _set_value(self, value):
        self._func, sval = value
        return super()._set_value(sval)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def is_leaf():
       return True
