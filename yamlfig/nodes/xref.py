from .scalar import ConfigScalar
from .composed import ComposedNode
from ..namespace import namespace, staticproperty


class XRefNode(ConfigScalar(str)):
    def __init__(self, value, **kwargs):
        super().__init__(value, **kwargs)

    @namespace('yamlfigns')
    def on_evaluate(self, path, ctx):
        chain = [ComposedNode.get_str_path(path)]
        curr = self
        while isinstance(curr, XRefNode):
            try:
                ref = ctx.yamlfigns.get_node(curr)
            except KeyError:
                msg = f'Referenced node {str(curr)!r} is missing, while following a chain of references: {chain}'
                raise ValueError(msg) from None

            chain.append(str(curr))
            curr = ref
        assert curr is not self
        return ctx.evaluate_node(curr, prefix=chain[-1])
        #return curr.yamlfigns.on_evaluate(path, ctx)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def tag():
        return '!xref'
