from .dict import ConfigDict
from .function import FunctionNode
from ..namespace import namespace, staticproperty
from ..utils import import_name


class CallNode(FunctionNode):
    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        if isinstance(self._func, str):
            self._func = import_name(self._func)
        args = ConfigDict.yamlfigns.on_evaluate(self, path, ctx)
        return self._func(**args)

    @namespace('yamlfigns')
    @property
    def tag(self):
        f = self._func
        if not isinstance(f, str):
            f = self._func.__module__ + '.' + self._func.__name__
        return '!call:' + f
