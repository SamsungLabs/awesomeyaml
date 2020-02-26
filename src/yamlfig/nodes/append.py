from .list import ConfigList
from ..namespace import namespace, staticproperty


class AppendNode(ConfigList):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_premerge(self, path, into):
        node = into.yamlfigns.remove_node(path)
        if node is None:
            raise KeyError(f'Node {str(self)!r} does not exist in the previous context (possibly deleted?) - while processing a {type(self).__name__!r} node at {path!r}')
        node.extend(self)
        return node
