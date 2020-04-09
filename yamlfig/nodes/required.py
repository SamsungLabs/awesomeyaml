from .node import ConfigNode
from ..namespace import namespace, staticproperty


class RequiredNode(ConfigNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        raise ValueError(f'RequiredNode should not appear during evaluation: {path!r}')

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!required'

    @namespace('yamlfigns')
    @property
    def value(self):
        return str()
