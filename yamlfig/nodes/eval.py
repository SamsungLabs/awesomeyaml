from .scalar import ConfigScalar
from .node import ConfigNode
from ..namespace import namespace, staticproperty
from ..errors import EvalError

import os
import sys
import copy


class EvalNode(ConfigScalar(str)):
    ''' Implements ``!eval`` tag.

        The eval node can be used to evaluate arbitrary python code.
        Internally, it is treated exactly as normal string node with the
        only exception being that on evaluation its value is passed to ``eval``.

        More specifically, the value obtained from evaluating an eval node is the
        value returned by the last line of code store in the node. If more lines are
        present, the preceding ones are executed before the last one to provide
        additional context (e.g., by defining functions, importing modules etc.).

        On top of that, the code stored in an eval node can use symbols defined
        by a relevant :py:class:`EvalContext` (please see its constructor)
        and can access all top-level nodes in the config by their names.

        The summary of the eval node's behaviour is illustrated by the following snippet::

            symbols = eval_context.get_eval_symbols()
            symbols.update(eval_context.get_top_level_objects_and_names())
            lines = str(self.code).split('\\n')
            exec('\\n'.join(lines[:-1]), symbols)
            return eval(lines[-1], symbols)

        Supported syntax::

            !eval code

        Merge behaviour:

            The same as standard string node.
    '''
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        gbls = copy.copy(ctx.get_eval_symbols())
        gbls.update(dict(ctx.yamlfigns.named_children()))
        lines = self.strip().split('\n')
        lines = [lline for line in lines for lline in line.split(';')]
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
