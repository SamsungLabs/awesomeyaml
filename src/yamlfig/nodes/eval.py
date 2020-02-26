from .scalar import ConfigScalar
from ..namespace import namespace

import copy


class EvalNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, root):
        gbls = copy.copy(globals())
        gbls.update(root._children)
        lines = self.strip().split('\n')
        exec("\n".join(lines[:-1]), gbls)
        return eval(lines[-1].strip(), gbls)
