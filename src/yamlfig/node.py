

class ConfigNode():
    def __init__(self, priority=None, weak=False):
        self._priority = priority
        self._weak = weak

    @staticmethod
    def is_leaf():
        return True
