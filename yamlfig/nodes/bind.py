from .dict import ConfigDict
from .function import FunctionNode
from ..namespace import namespace, staticproperty
from ..utils import import_name

from functools import partial


class BindNode(FunctionNode):
    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        if isinstance(self._func, str):
            self._func = import_name(self._func)
        args = ConfigDict.yamlfigns.on_evaluate(self, path, ctx)
        return partial(self._func, **args)

    @namespace('yamlfigns')
    @property
    def tag(self):
        return '!bind:' + self._func
