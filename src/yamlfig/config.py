from .nodes.dict import ConfigDict
from .nodes.node import ConfigNodeMeta
from .namespace import namespace, staticproperty

import collections


class ConfigMeta(ConfigNodeMeta):
    def __call__(cls, value=None, idx=None, raw_yaml=None, filename=None):
        ''' `value` can be: str (either a filename or yaml), file object, or a list of those
        '''
        if isinstance(value, dict) or value is None:
            obj = cls.__new__(cls, value)
            obj.__init__(value=value, idx=idx)
            return obj
        else:
            from .builder import Builder
            b = Builder()
            if not isinstance(value, collections.Sequence) or isinstance(value, str):
                b.add_source(value, raw_yaml=raw_yaml, filename=filename)
            else:
                b.add_multiple_sources(*value, raw_yaml=raw_yaml, filename=filename)
            return Config(value=b.build(), idx=idx)


class Config(ConfigDict, metaclass=ConfigMeta):
    def __init__(self, value=None, idx=None, raw_yaml=None):
        super().__init__(value=value, idx=idx)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def is_root():
        return True
