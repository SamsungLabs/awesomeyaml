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
from ..utils import Bunch, python_is_at_least
from ..errors import EvalError

import os
import dis
import sys
import types
import hashlib


class GlobalsWrapper():
    def __init__(self, gbls, ecfg, ctx, node, path):
        self.gbls = gbls
        self.ecfg = ecfg
        self.ctx = ctx
        self.node = node
        self.path = path

    def __getattr__(self, name):
        if name in self.gbls:
            return self.gbls[name]

        if name in self.ecfg._cfgobj:
            with self.ctx.require_all_safe(self.node, self.path):
                return self.ecfg[name]
        elif name in __builtins__:
            return __builtins__[name]
        else:
            raise NameError(name)

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
    _globals_wrapper_name = '__ayns_globals_wrapper'

    def __init__(self, value, persistent_namespace=True, **kwargs):
        super().__init__(value, **kwargs)
        self.persistent_namespace = persistent_namespace

    @namespace('ayns')
    def on_evaluate_impl(self, path, ctx):
        self.ayns._require_safe(path)
        code_hash = hashlib.md5(str(self).encode('utf-8')).hexdigest()
        eval_module_name = f'{EvalNode._top_namespace_module_name}.{str(path).replace(".", "_")}_0x{code_hash}'

        from_module = False
        if self.persistent_namespace and eval_module_name in sys.modules:
            gbls = sys.modules[eval_module_name].__dict__
            from_module = True
        else:
            gbls = {
                'ayns': Bunch({
                    'ctx': ctx,
                    'cfg': ctx.ecfg
                })
            }
            gbls.update(ctx.get_eval_symbols())
            gbls.update({ '__name__': eval_module_name, '__file__': self._source_file })

        gbls[EvalNode._globals_wrapper_name] = GlobalsWrapper(gbls, ctx.ecfg, ctx, self, path)

        lines = self.strip().split('\n')
        lines = [lline for line in lines for lline in line.split(';')]

        exec_lines = "\n".join(lines[:-1])
        eval_line = lines[-1].strip()

        try:
            exec_code = compile(exec_lines, self._source_file, 'exec')
            eval_code = compile(eval_line, self._source_file, 'eval')
            exec_code_patched, _ = EvalNode._patch_access_to_globals(exec_code)
            eval_code_patched, _ = EvalNode._patch_access_to_globals(eval_code)
            exec(exec_code_patched, gbls)
            ret = eval(eval_code_patched, gbls)
        except EvalError as e:
            code = f'=== CODE BEGINS ===\n{os.linesep.join(lines)}\n=== CODE ENDS ==='
            if e.node is self:
                e.note = code
                raise
            else:
                raise EvalError('The above exception occurred in the user code.', self, path, note=code) from e
        except Exception as e:
            code = f'=== CODE BEGINS ===\n{os.linesep.join(lines)}\n=== CODE ENDS ==='
            raise EvalError('The above exception occurred in the user code.', self, path, note=code) from e

        del gbls[EvalNode._globals_wrapper_name]

        if len(lines) > 1 and self.persistent_namespace and not from_module:
            eval_node_module = types.ModuleType(eval_module_name, 'Dynamic module to evaluate awesomeyaml !eval node')
            eval_node_module.__dict__.update(gbls)
            sys.modules[eval_module_name] = eval_node_module

        if isinstance(ret, ConfigNode):
            assert ret is not self
            ret = ctx.evaluate_node(ret, path)
        return ret

    @namespace('ayns')
    @staticproperty
    @staticmethod
    def tag():
        return '!eval'


    @staticmethod
    def _patch_access_to_globals(code):
        done_something = False

        def maybe_patch(const):
            if isinstance(const, types.CodeType):
                nonlocal done_something
                new_const, done_something_sub = EvalNode._patch_access_to_globals(const)
                if done_something_sub:
                    done_something = True
                return new_const

            return const

        new_consts = [maybe_patch(const) for const in code.co_consts]
        new_names = list(code.co_names)
        has_wrapper = bool(EvalNode._globals_wrapper_name in new_names)

        _wrapper_idx = None
        def get_wrapper_index():
            nonlocal _wrapper_idx
            if _wrapper_idx is None:
                if has_wrapper:
                    _wrapper_idx = new_names.index(EvalNode._globals_wrapper_name)
                else:
                    new_names.append(EvalNode._globals_wrapper_name)
                    _wrapper_idx = len(new_names) - 1

            assert _wrapper_idx is not None
            return _wrapper_idx


        new_bytecode = []
        rjumps = []
        ajumps = []
        location_map = {}

        i = 0
        while i < len(code.co_code):
            done = False
            op = code.co_code[i]
            if dis.opname[op] in ['LOAD_GLOBAL', 'LOAD_NAME']:
                arg = code.co_code[i+1]
                arg_shifted = (python_is_at_least(3, 11) and dis.opname[op] == 'LOAD_GLOBAL')

                if arg_shifted:
                    null_bit = arg & 0x01
                    arg = arg>>1

                name = code.co_names[arg]

                if name not in ['__ayns_globals_wrapper', 'ayns']:
                    new_arg = get_wrapper_index()
                    if arg_shifted:
                        new_arg = (new_arg << 1) | null_bit

                    location_map[i//2] = len(new_bytecode)
                    new_bytecode.append(code.co_code[i:i+1] + new_arg.to_bytes(1, 'little'))
                    if python_is_at_least(3, 11):
                        caches = dis._inline_cache_entries[op]
                        for _ in range(caches):
                            assert i+2 < len(code.co_code)
                            assert code.co_code[i+2] == 0
                            new_bytecode.append(code.co_code[i+2:i+4])
                            i += 2

                    new_bytecode.append(dis.opmap['LOAD_ATTR'].to_bytes(1, 'little') + arg.to_bytes(1, 'little'))
                    if python_is_at_least(3, 11):
                        caches = dis._inline_cache_entries[dis.opmap['LOAD_ATTR']]
                        for _ in range(caches):
                            new_bytecode.append(b'\x00\x00') # CACHE(0)

                    done_something = True
                    done = True
            elif op in dis.hasjabs:
                ajumps.append(len(new_bytecode))
            elif op in dis.hasjrel:
                rjumps.append(len(new_bytecode))

            if not done:
                location_map[i//2] = len(new_bytecode)
                new_bytecode.append(code.co_code[i:i+2])

            i += 2

        if not done_something:
            return code, False

        rlocation_map = { value: key for key, value in location_map.items() }

        for rjump in rjumps:
            new_jump_loc = rjump
            old_jump_loc = rlocation_map[new_jump_loc]

            op, old_loc_rel = new_bytecode[rjump]
            is_backward = False
            if python_is_at_least(3, 11) and 'BACKWARD' in dis.opname[op]:
                is_backward = True

            if not python_is_at_least(3, 10): # python 3.10 starts counting instructions (each 2-bytes long), before that it was counting bytes
                # in this code the convention is to count instructions (e.g., because of the way "new_bytecode" is organized), so translate
                # offset from bytes to instructions
                old_loc_rel //= 2

            if is_backward:
                old_loc_abs = old_jump_loc - old_loc_rel
            else:
                old_loc_abs = old_loc_rel + old_jump_loc

            new_loc_abs = location_map[old_loc_abs]
            new_loc_rel = abs(new_loc_abs - new_jump_loc)
            if not python_is_at_least(3, 10):
                new_loc_rel *= 2

            new_bytecode[rjump] = op.to_bytes(1, 'little') + new_loc_rel.to_bytes(1, 'little')

        for ajump in ajumps:
            op, old_loc_abs = new_bytecode[ajump]
            if not python_is_at_least(3, 10):
                old_loc_abs //= 2
            new_loc_abs = location_map[old_loc_abs]
            if not python_is_at_least(3, 10):
                new_loc_abs *= 2
            new_bytecode[ajump] = op.to_bytes(1, 'little') + new_loc_abs.to_bytes(1, 'little')


        new_bytecode = b''.join(new_bytecode)
        if python_is_at_least(3, 11):
            return types.CodeType(code.co_argcount,
                                    code.co_posonlyargcount, # only in Python >= 3.8
                                    code.co_kwonlyargcount,
                                    code.co_nlocals,
                                    code.co_stacksize,
                                    code.co_flags,
                                    new_bytecode,
                                    tuple(new_consts),
                                    tuple(new_names),
                                    code.co_varnames,
                                    code.co_filename,
                                    code.co_name,
                                    code.co_qualname, # only in Python >= 3.11
                                    code.co_firstlineno,
                                    code.co_lnotab,
                                    code.co_exceptiontable, # only in Python >= 3.11
                                    code.co_freevars,
                                    code.co_cellvars), True
        elif python_is_at_least(3, 8):
            return types.CodeType(code.co_argcount,
                                    code.co_posonlyargcount, # only in Python >= 3.8
                                    code.co_kwonlyargcount,
                                    code.co_nlocals,
                                    code.co_stacksize,
                                    code.co_flags,
                                    new_bytecode,
                                    tuple(new_consts),
                                    tuple(new_names),
                                    code.co_varnames,
                                    code.co_filename,
                                    code.co_name,
                                    code.co_firstlineno,
                                    code.co_lnotab,
                                    code.co_freevars,
                                    code.co_cellvars), True
        else:
            return types.CodeType(code.co_argcount,
                                    code.co_kwonlyargcount,
                                    code.co_nlocals,
                                    code.co_stacksize,
                                    code.co_flags,
                                    new_bytecode,
                                    tuple(new_consts),
                                    tuple(new_names),
                                    code.co_varnames,
                                    code.co_filename,
                                    code.co_name,
                                    code.co_firstlineno,
                                    code.co_lnotab,
                                    code.co_freevars,
                                    code.co_cellvars), True
