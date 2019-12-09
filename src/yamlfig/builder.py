

class Builder():
    def __init__(self):
        self.stages = []

    def get_current_stage_idx(self):
        return len(self.stages)

    def add_stages(self, source, raw_yaml=None):
        ''' Parse a stream of yaml documents specified by `source` and add them to the list of stages.
            The documents stream can be provided either directly or read from a file - the behaviour is determined
            by `source` and `raw_yaml` arguments.
            Args:
                `source` - either a string or a file object. If it's a file object, it will be passed directly to the `yamlfig.yaml.parse`,
                           otherwise it will be treated either as a filename or yaml to be parsed, according to `raw_yaml`.
                `raw_yaml` - controls how `source` is interpreted if it is passed as string, possible cases are:
                                 - if `raw_yaml` is set to `None` specifically (default), the function will try guessing whether `source` is a
                                   name of a file or a yaml string to be parsed directly. In order to do that, it will behave as if `raw_yaml` was set to `False`
                                   and in case `FileNotFoundError` is raised, it will fallback to the case when `raw_yaml` is set to `True`.
                                - if `bool(raw_yaml)` evalues to `False` and is not None, the function will attempt to open and read content of a file named `source`,
                                  raising an error if such a file does not exist
                                - if `bool(raw_yaml)` evalues to `True`, `source` is treated as a yaml string and passed directly to the `yamlfig.yaml.parse`
            Returns:
                None
        '''
        if raw_yaml and not isinstance(source, str):
            raise ValueError('source is expected to be string and contain yaml to be parsed when raw_yaml is set to True')

        if isinstance(source, str) and not raw_yaml:
            try:
                with open(source, 'r') as f:
                    source = f.read()
            except (FileNotFoundError, OSError) as e:
                #OSError(22) is "Invalid argument"
                if type(e) is OSError and e.errno != 22:
                    raise
                if raw_yaml is not None:
                    raise

        from . import yaml
        for node in yaml.parse(source, self):
            if node is not None:
                self.stages.append(node)

    def build(self):
        from .config import Config
        if not self.stages:
            return Config()

        self.process_includes()
        self.flatten()
        self.evaluate()
        return Config(self.stages[0])

    def process_includes(self):
        pass

    def flatten(self):
        if len(self.stages) < 2:
            return

        for i in range(1, len(self.stages)):
            self.stages[0].merge(self.stages[i])

        self.stages = [self.stages[0]]

    def evaluate(self):
        pass
