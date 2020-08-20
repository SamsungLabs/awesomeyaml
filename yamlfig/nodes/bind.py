from .dict import ConfigDict
from .function import FunctionNode
from ..namespace import namespace, staticproperty
from ..utils import import_name

from functools import partial


class BindNode(FunctionNode):
    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        _func = self._func
        if isinstance(_func, str):
            _func = import_name(_func)
        args = ConfigDict.yamlfigns.on_evaluate(self, path, ctx)
        p, kw_p, kw = FunctionNode._resolve_args(_func, args)
        return partial(_func, *p, **kw_p, **kw)

    @namespace('yamlfigns')
    @property
    def tag(self):
        _func = self._func
        if not isinstance(_func, str):
            _func = self._func.__module__ + '.' + self._func.__name__
        return '!bind:' + _func
