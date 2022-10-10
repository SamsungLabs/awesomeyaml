# Copyright 2022 Samsung Electronics Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .scalar import ConfigScalar
from .node import ConfigNode
from ..namespace import namespace, staticproperty
from ..errors import EvalError
from ..utils import Bunch

import os
import sys
import copy
import types
import ctypes
import hashlib


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
    _top_namespace_module_name = 'awesomeyaml.eval_node_namespace'

    def __init__(self, value, persistent_namespace=True, source_file=None, **kwargs):
        super().__init__(value, **kwargs)
        self.persistent_namespace = persistent_namespace

    @namespace('ayns')
    def on_evaluate(self, path, ctx):
        code_hash = hashlib.md5(str(self).encode('utf-8')).hexdigest()
        eval_module_name = f'{EvalNode._top_namespace_module_name}.{str(path).replace(".", "_")}_0x{code_hash}'

        lcls = ctx.ecfg
        gbls = {
            'ayns': Bunch({
                'ctx': ctx,
                'cfg': lcls
            })
        }
        gbls.update(ctx.get_eval_symbols())
        gbls.update({ '__name__': eval_module_name, '__file__': self._source_file })

        lines = self.strip().split('\n')
        lines = [lline for line in lines for lline in line.split(';')]
        try:
            exec("\n".join(lines[:-1]), gbls, lcls)
            ret = eval(lines[-1].strip(), gbls, lcls)
        except:
            et, e, _ = sys.exc_info()
            raise EvalError(f'Exception occurred while evaluation an eval node {path!r} from file {str(self.ayns.source_file)!r}:\n\nCode:\n{os.linesep.join(lines)}\n\nError:\n{et.__name__}: {e}') from None

        if len(lines) > 1 and self.persistent_namespace:
            eval_node_module = types.ModuleType(eval_module_name, 'Dynamic module to evaluate awesomeyaml !eval node')
            eval_node_module.__dict__.update(gbls)
            sys.modules[eval_module_name] = eval_node_module

        if isinstance(ret, ConfigNode):
            assert ret is not self
            ret = ret.ayns.on_evaluate(path, ctx)
        return ret

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!eval'
