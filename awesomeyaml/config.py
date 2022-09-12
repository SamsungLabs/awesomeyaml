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

import copy
import collections.abc as cabc

from .nodes.dict import ConfigDict
from .eval_context import EvalContext
from .namespace import namespace, NamespaceableMeta
from .utils import Bunch
from .nodes.required import RequiredNode


class Config(Bunch, metaclass=NamespaceableMeta):
    ''' A class representing parsed and evaluated config dictionary.
    '''
    def __init__(self, config_dict=None):
        ''' Arguments:
                config_dict : `dict` or unevaluated `awesomeyaml.nodes.ConfigDict`, `None`
                    represents an empty dict.
        '''
        if config_dict is not None and not isinstance(config_dict, dict):
            raise ValueError('dict or None expected')

        if not isinstance(config_dict, ConfigDict):
            config_dict = ConfigDict(config_dict)

        if config_dict:
            Config.check_missing(config_dict)
            self._source = config_dict
            pre_evaluate = copy.deepcopy(config_dict)
            eval_ctx = EvalContext(pre_evaluate)
            evaluated = eval_ctx.evaluate()
        else:
            evaluated = {}

        super().__init__(evaluated)

    @classmethod
    def build(cls, *sources, raw_yaml=None, filename=None):
        ''' Builds a config from the provided yaml sources and evaluates it, returning `awesomeyaml.Config` object.

            Arguments:
                *sources : a list of yaml sources - that can include file-like objects, filenames and strings of yaml
                raw_yaml : 
        '''
        from .builder import Builder
        b = Builder()
        b.add_multiple_sources(*sources, raw_yaml=raw_yaml, filename=filename)
        return Config(b.build())

    @classmethod
    def process_cmdline(cls, args, filename_lookup_fn=None):
        yamls = []
        filenames = []
        raw_yamls = []

        def append(idx, option):
            if option.startswith('{') and option.endswith('}'):
                yaml = option
                filename = f'<Commandline argument #{idx}>'
                raw_yaml = True
            elif '=' in option:
                key, value = option.split('=', maxsplit=1)
                yaml = ''
                ind = 0
                for part in key.split('.'):
                    if ind:
                        yaml += '\n'
                        yaml += '    ' * ind

                    yaml += part + ': '
                    ind += 1

                yaml += value
                filename = f'<Commandline argument #{idx}>'
                raw_yaml = True
            else:
                yaml = option
                if filename_lookup_fn is not None:
                    yaml = filename_lookup_fn(yaml)
                filename = yaml
                raw_yaml = False

            yamls.append(yaml)
            filenames.append(filename)
            raw_yamls.append(raw_yaml)

        for i, src in enumerate(args):
            append(i, src)

        return yamls, filenames, raw_yamls

    @classmethod
    def build_from_cmdline(cls, *sources, filename_lookup_fn=None):
        yamls, filenames, raw_yamls = cls.process_cmdline(sources, filename_lookup_fn=filename_lookup_fn)
        return cls.build(*yamls, raw_yaml=raw_yamls, filename=filenames)

    @staticmethod
    def check_missing(cfg):
        missing = []
        for path, node in cfg.ayns.nodes_with_paths():
            if isinstance(node, RequiredNode):
                missing.append(repr(path))

        if missing:
            raise ValueError('The following required nodes have not been set:\n    ' + '\n    '.join(missing))

    @namespace('ayns')
    @property
    def source(self):
        ''' The source `awesomeyaml.nodes.ConfigDict` which was evaluated to construct
            this `awesomeyaml.Config`.
        '''
        return self._source

    @namespace('ayns')
    def pprint(self, ind=2, init_level=0):
        import io
        import functools

        try:
            import torch.nn as nn
        except:
            nn = None

        ind = ' '*ind
        ret = '' #ind*init_level
        stack = [[self, init_level, None]]
        emitted_recently = False
        offset = 0
        while stack:
            frame = stack[-1]
            obj, level, i = frame
            to_emit = obj
            finished = False
            emit = False
            if i is None:
                if isinstance(obj, functools.partial):
                    args = obj.keywords.copy()
                    if obj.args:
                        args.update({ idx: arg for idx, arg in enumerate(obj.args) })

                    to_emit = obj.func
                    obj = args
                    frame[0] = obj
                    emit = True
                elif nn is not None and isinstance(obj, nn.Module):
                    obj = f'<Neural network of type \'{type(obj).__module__}.{type(obj).__qualname__}\' with {sum(p.numel() for p in obj.parameters())} parameters and {sum(1 for _ in obj.modules())} submodules>'
                    to_emit = obj


                if not isinstance(obj, (cabc.Sequence, cabc.Mapping)) or isinstance(obj, (str, bytes, io.IOBase)):
                    finished = True
                    emit = True
                    if isinstance(obj, str) and '\n' in obj:
                        str_ind = ind*(level+1)+'    '
                        line_ind = str_ind + '    '
                        to_emit = '\n' + str_ind + "''' " + f'\n{line_ind}'.join(obj.rstrip().split('\n')) + '\n' + str_ind + "'''\n"
                else:
                    try:
                        i = iter(obj)
                    except TypeError:
                        finished = True
                        emit = True
                    else:
                        if not obj:
                            finished = True
                            emit = True
                            i = None
                        elif Config._pprint_is_simple_list(obj):
                            offset_fix = 0
                            if len(stack) > 1 and isinstance(stack[-2][0], dict):
                                offset_fix = 1 # account for the extra space that is added in the `elif emit:` block below
                            to_emit = Config._pprint_format_simple_list(obj, ind*level, width_limit=160, offset=offset+offset_fix)
                            finished = True
                            emit = True
                            i = None

                if not finished:
                    frame[2] = i
                    if len(stack) > 1 and isinstance(stack[-2][0], dict): # if a dict contains a collection, add newline after key
                        if not emit:
                            ret += '\n'
                            offset = 0
                        else: # the same as below, but special case when `not finished and emit`
                            ret += ' '
                            offset += 1
                elif emit:
                    if len(stack) > 1 and isinstance(stack[-2][0], dict): # if a dict contains an empty collection or scalar value, add space after key
                        ret += ' '
                        offset += 1

            if emit:
                try:
                    ret += str(to_emit)
                except ValueError:
                    ret += repr(to_emit)
                ret += '\n'
                offset = 0
                emitted_recently = True

            if not finished:
                try:
                    child = next(i)
                except StopIteration:
                    finished = True
                else:
                    if isinstance(obj, dict):
                        ret += ind*level
                        ret += str(child)
                        ret += ':'
                        offset += len(ind) * level + len(str(child)) + 1
                        child = obj[child]
                    else:
                        ret += ind*level
                        ret += '- '
                        offset += len(ind) * level + 2

                    stack.append([child, level+1, None])

            if finished:
                stack.pop()
                # we finished a non-empty interable, add extra newline
                if i is not None and emitted_recently:
                    ret += '\n'
                    offset = 0
                    emitted_recently = False

        return ret

    @staticmethod
    def _pprint_is_simple_list(obj):
        if isinstance(obj, cabc.Sequence) and not isinstance(obj, (str, bytes)):
            if all(isinstance(e, (int, float)) or (isinstance(e, str) and len(e) < 25 and '\n' not in e) for e in obj):
                return True
        return False

    @staticmethod
    def _pprint_format_simple_list(obj, ind, width_limit=160, offset=0):
        width_limit += max(0, max(len(ind), offset) - width_limit + 40) # make sure we have at least 40 characters per line, violate width limit if necessary
        ret = ''
        line = ''
        sep = '['
        size = len(obj)
        for i, e in enumerate(obj):
            to_add = sep + repr(e)
            if i+1 < size:
                to_add += ','
            else:
                to_add += ']'

            if len(line) + len(to_add) + offset >= width_limit:
                ret += line + '\n'
                line = ind + to_add
                offset = 0
            else:
                line += to_add
                sep = ' '

        ret += line
        return ret
