import copy

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
                config_dict : `dict` or unevaluated `yamlfig.nodes.ConfigDict`, `None`
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
        ''' Builds a config from the provided yaml sources and evaluates it, returning `yamlfig.Config` object.

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
            if '=' in option:
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
        for path, node in cfg.yamlfigns.nodes_with_paths():
            if isinstance(node, RequiredNode):
                missing.append(repr(path))

        if missing:
            raise ValueError('The following required nodes have not been set:\n    ' + '\n    '.join(missing))

    @namespace('yamlfigns')
    @property
    def source(self):
        ''' The source `yamlfig.nodes.ConfigDict` which was evaluated to construct
            this `yamlfig.Config`.
        '''
        return self._source

    @namespace('yamlfigns')
    def pprint(self, ind=2, init_level=0):
        import io
        import functools

        ind = ' '*ind
        ret = '' #ind*init_level
        stack = [[self, init_level, None]]
        emitted_recently = False
        while stack:
            frame = stack[-1]
            obj, level, i = frame
            to_emit = obj
            finished = False
            emit = False
            if i is None:
                if isinstance(obj, functools.partial):
                    assert not obj.args
                    to_emit = obj.func
                    obj = obj.keywords
                    frame[0] = obj
                    emit = True

                if isinstance(obj, str) or isinstance(obj, bytes) or isinstance(obj, io.IOBase):
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

                if not finished:
                    frame[2] = i
                    if len(stack) > 1 and isinstance(stack[-2][0], dict): # if a dict contains a collection, add newline after key
                        if not emit:
                            ret += '\n'
                        else: # the same as below, but special case when `not finished and emit`
                            ret += ' '
                elif emit:
                    if len(stack) > 1 and isinstance(stack[-2][0], dict): # if a dict contains an empty collection or scalar value, add space after key
                        ret += ' '

            if emit:
                try:
                    ret += str(to_emit)
                except ValueError:
                    ret += repr(to_emit)
                ret += '\n'
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
                        child = obj[child]
                    else:
                        ret += ind*level
                        ret += '- '

                    stack.append([child, level+1, None])

            if finished:
                stack.pop()
                # we finished a non-empty interable, add extra newline
                if i is not None and emitted_recently:
                    ret += '\n'
                    emitted_recently = False

        return ret
