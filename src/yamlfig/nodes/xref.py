from .scalar import ConfigScalar
from .composed import ComposedNode
from ..namespace import namespace


class XRefNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, root):
        chain = [ComposedNode.get_str_path(path)]
        curr = self
        while isinstance(curr, XRefNode):
            ref = root.yamlfigns.get_node(curr)
            if ref is None:
                msg = f'Referenced node {str(curr)!r} is missing, while following a chain of references: {chain}'
                raise ValueError(msg)
            chain.append(str(curr))
            curr = ref
        return curr
