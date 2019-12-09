class DelNode(ConfigNode):
    def __init__(self, value):
        self.value = value

    def _get_raw_value(self):
        return self.value
