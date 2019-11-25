from .node import ConfigNode

class ConfigList(ConfigNode):
    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def is_leaf():
        return False
