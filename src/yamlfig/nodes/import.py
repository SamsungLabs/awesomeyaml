from .scalar import ConfigScalar
from ..namespace import namespace
from ..utils import import_name


class ImportNode(ConfigScalar(str)):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, root):
        return import_name(self)

