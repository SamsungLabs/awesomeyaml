from .scalar import ConfigScalar
from .node import ConfigNode
from ..namespace import namespace, staticproperty
from ..errors import EvalError

import os
import sys
import copy


class EvalNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        gbls = copy.copy(ctx.get_eval_symbols())
        gbls.update(dict(ctx.yamlfigns.named_children()))
        lines = self.strip().split('\n')
        try:
            exec("\n".join(lines[:-1]), gbls)
            ret = eval(lines[-1].strip(), gbls)
        except:
            et, e, _ = sys.exc_info()
            raise EvalError(f'Exception occurred while evaluation an eval node {path!r} from file {str(self.yamlfigns.source_file)!r}:\n\nCode:\n{os.linesep.join(lines)}\n\nError:\n{et.__name__}: {e}') from None

        if isinstance(ret, ConfigNode):
            assert ret is not self
            ret = ret.on_evaluate(path, ctx)
        return ret

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!eval'
