from .node import ConfigNode
from .dynamic import DynamicNode
from .. import yaml


class IncludeNodeMeta(type):
    def __call__(cls, filename):
        if not isinstance(filename, str):
            raise ValueError(f'Include node expects a string parameter with a filename to read, but got: {type(filename)}')

        with open(filename, 'r') as file:
            return yaml.parse_config(file)

class IncludeNode(metaclass=IncludeNodeMeta):
    def __init__(self, *args, **kwargs):
        raise RuntimeError('IncludeNode should never be constructed')
