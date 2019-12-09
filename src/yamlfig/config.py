from .nodes.dict import ConfigDict
from .nodes.node import ConfigNodeMeta
from .namespace import namespace, staticproperty


class ConfigMeta(ConfigNodeMeta):
    def __call__(cls, value=None, idx=None, raw_yaml=None):
        if isinstance(value, dict) or value is None:
            obj = cls.__new__(cls, value)
            obj.__init__(value=value, idx=idx)
            return obj
        else:
            from .builder import Builder
            b = Builder()
            b.add_stages(value, raw_yaml=raw_yaml)
            return b.build()


class Config(ConfigDict, metaclass=ConfigMeta):
    def __init__(self, value=None, idx=None, raw_yaml=None):
        super().__init__(value=value, idx=idx)

    @namespace('node_info')
    @staticproperty
    @staticmethod
    def is_root():
        return True
