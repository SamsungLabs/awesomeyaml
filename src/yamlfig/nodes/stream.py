from .list import ConfigList

from ..namespace import namespace, staticproperty


class StreamNode(ConfigList):
    def __init__(self, builder, **kwargs):
        super().__init__(builder.stages, **kwargs)
        self.builder = builder

    @property
    def stages(self):
        return self.builder.stages

    @namespace('yamlfigns')
    def on_premerge(self, path, into):
        self.clear()
        self.builder.flatten()
        self.append(self.builder.stages[0])
        return self.builder.stages[0].yamlfigns.on_premerge(path, into)

    @namespace('yamlfigns')
    @staticproperty
    @staticmethod
    def is_leaf():
        return True
