from .scalar import ConfigScalar
from .node import ConfigNode
from ..namespace import namespace

import copy


class EvalNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        gbls = copy.copy(globals())
        gbls.update(dict(ctx.yamlfigns.named_children()))
        lines = self.strip().split('\n')
        exec("\n".join(lines[:-1]), gbls)
        ret = eval(lines[-1].strip(), gbls)
        if isinstance(ret, ConfigNode):
            assert ret is not self
            ret = ret.on_evaluate(path, ctx)
        return ret
