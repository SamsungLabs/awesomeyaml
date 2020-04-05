from .nodes.dict import ConfigDict
from .eval_context import EvalContext
from .utils import Bunch


class Config(Bunch):
    ''' A class representing parsed and evaluated config dictionary.
    '''
    def __init__(self, config_dict=None):
        ''' Arguments:
                config_dict : `dict` or unevaluated `yamlfig.nodes.ConfigDict`, `None`
                    represents an empty dict.
        '''
        if config_dict is not None and not isinstance(config_dict, dict):
            raise ValueError('dict or None expected')

        _old = config_dict
        config_dict = ConfigDict(config_dict)
        assert not isinstance(_old, ConfigDict) or config_dict is _old
        if config_dict:
            self._source = config_dict
            pre_evaluate = config_dict.yamlfigns.deepcopy()
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

    @property
    def source(self):
        ''' The source `yamlfig.nodes.ConfigDict` which was evaluated to construct
            this `yamlfig.Config`.
        '''
        return self._source
