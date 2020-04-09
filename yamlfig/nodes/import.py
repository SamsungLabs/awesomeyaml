from .scalar import ConfigScalar
from ..namespace import namespace, staticproperty
from ..utils import import_name


class ImportNode(ConfigScalar(str)):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        return import_name(str(self))

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!import'
