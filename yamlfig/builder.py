import os
import contextlib
import collections


class Builder():
    def __init__(self):
        self.stages = []
        self._current_file = None
        self._current_stage = None

    @contextlib.contextmanager
    def current_stage(self, i):
        old = self._current_stage
        self._current_stage = i
        yield
        self._current_stage = old

    def get_next_stage_idx(self):
        return len(self.stages)

    def get_current_stage_idx(self):
        return self._current_stage

    def get_current_file(self):
        return self._current_file

    def add_multiple_sources(self, *sources, raw_yaml=None, filename=None):
        def sanitize(arg, arg_name):
            if not isinstance(arg, collections.Sequence) or isinstance(arg, str) or isinstance(arg, bytes):
                arg = [arg] * len(sources)
            else:
                #if isinstance(arg, str) or isinstance(arg, bytes):
                #    raise ValueError(f"{arg_name!r}: Expected sequence but not str or bytes")
                if len(arg) != len(sources):
                    raise ValueError(f"Length of 'sources' and {arg_name!r} must match")

            return arg

        raw_yaml = sanitize(raw_yaml, 'raw_yaml')
        filename = sanitize(filename, 'filename')
        for source, raw, fname in zip(sources, raw_yaml, filename):
            self.add_source(source, raw_yaml=raw, filename=fname)

    def add_source(self, source, raw_yaml=None, filename=None):
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
                                - if `bool(raw_yaml)` evaluates to `False` and is not None, the function will attempt to open and read content of a file named `source`,
                                  raising an error if such a file does not exist
                                - if `bool(raw_yaml)` evaluates to `True`, `source` is treated as a yaml string and passed directly to the `yamlfig.yaml.parse`
            Returns:
                None
        '''
        if raw_yaml and not isinstance(source, str):
            raise ValueError('source is expected to be string and contain yaml to be parsed when raw_yaml is set to True')

        if isinstance(source, str) and not raw_yaml:
            try:
                with open(source, 'r') as f:
                    self._current_file = source
                    source = f.read()
            except (FileNotFoundError, OSError) as e:
                #OSError(22) is "Invalid argument"
                if type(e) is OSError and e.errno != 22:
                    raise
                if raw_yaml is not None:
                    raise

        try:
            if filename is not None:
                self._current_file = filename

            from . import yaml
            for node in yaml.parse(source, self):
                if node is not None:
                    self.stages.append(node)
        finally:
            self._current_file = None

    def build(self):
        if not self.stages:
            return None

        self.preprocess()
        self.flatten()
        return self.stages[0]

    def preprocess(self):
        i = 0
        while i < len(self.stages):
            _i = i
            with self.current_stage(i):
                stage = self.stages[i]
                new_stage = stage.yamlfigns.preprocess(self)

                if new_stage is not stage:
                    try:
                        self.stages[i:i+1] = new_stage.stages
                        i += len(new_stage.stages)
                    except AttributeError:
                        self.stages[i] = new_stage
                        i += 1
                else:
                    i += 1

            assert _i != i, 'infinite loop?'

    def flatten(self):
        for stage in self.stages:
            if not isinstance(stage, dict):
                raise ValueError('Not all stages are dictionaries')

        new_stage = self.stages[0].yamlfigns.premerge(None)
        if new_stage is not self.stages[0]:
            try:
                self.stages[0:1] = new_stage.stages
            except AttributeError:
                self.stages[0] = new_stage

        if len(self.stages) < 2:
            return

        for i in range(1, len(self.stages)):
            self.stages[0].yamlfigns.merge(self.stages[i])

        self.stages = [self.stages[0]]

    def get_lookup_dirs(self, ref_point):
        if ref_point is not None:
            yield os.path.dirname(ref_point)
        yield os.getcwd()

    def get_subbuilder(self, requester):
        if self._current_stage is None:
            raise RuntimeError('SubBuilder requested when not processing any stage!')

        return SubBuilder(requester, self)


class SubBuilder(Builder):
    def __init__(self, srcnode, parent):
        super().__init__()
        self.requester = srcnode
        self.parent = parent
        self.stage = parent.get_current_stage_idx()

    def build(self):
        from .nodes.stream import StreamNode
        self.preprocess()
        return StreamNode(self)

    def get_lookup_dirs(self, ref_point):
        return self.parent.get_lookup_dirs(ref_point)
