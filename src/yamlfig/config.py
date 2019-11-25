from .node import ConfigNode


class Config(ConfigNode):
    def __init__(self, value=None, **kwargs):
        super().__init__(**kwargs)

    def merge(self, other):


    @staticmethod
    def is_leaf():
        return False

    @staticmethod
    def from_file(filename):
        from . import yaml
        with open(filename, 'r') as f:
            base, *rest = yaml.parse_config(f.read())
            if not base:
                return Config()

            base = Config(base)

        for next_cfg in rest:
            base.merge(Config(next_cfg))

        return base
