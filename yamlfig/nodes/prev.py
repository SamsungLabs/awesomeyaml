from .scalar import ConfigScalar
from ..namespace import namespace, staticproperty


class PrevNode(ConfigScalar(str)):
    def __init__(self, ref, **kwargs):
        super().__init__(ref)

    @namespace('yamlfigns')
    def on_premerge(self, path, into):
        node = into.yamlfigns.remove_node(self)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?) - while processing a {type(self).__name__!r} node at {path!r}')
        return node

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!prev'
