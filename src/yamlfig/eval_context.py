import functools

from .nodes.composed import ComposedNode
from .nodes.delete import DelNode


class EvalContext():
    def __init__(self, sources):
        self.sources = tuple(sources)

    def __repr__(self):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x} with {len(self.sources)} sources>'

    def __str__(self):
        return '---\n'.join(map(str, self.sources))

    def get_node(self, *path, default=ValueError):
        str_path = ComposedNode.get_str_path(*path)
        if not self.sources:
            if not default:
                raise KeyError('Node with path: {str_path!r} does not exists in an eval context {self!r}')
        if len(self.sources) == 1:
            return self.sources[0].get_node(path, return_intermediate=False, include_names=False, allow_incomplete=None)

        candidate = None
        start = None

        candidate, index = self.rfind(name, start=None, return_intermediate=True, include_names=True)
        start = index - 1

        # Check for 'weak' and 'force'
        while not candidate[-1][1].yamlfigns.force:
            try:
                override, index2 = self.rfind(name, start=start, return_intermediate=True, include_names=True)
                start = index2 - 1
                if (candidate[-1][1].yamlfigns.weak and not override[-1][1].yamlfigns.weak) or (not candidate[-1][1].yamlfigns.force and override[-1][1].yamlfigns.force):
                    candidate = override
                    index = index2
            except KeyError:
                break

    def get_node_dels(self, name):
        ret = []
        path = EvalContext.split_name(name)
        for i, source in enumerate(self.sources):
            nodes = EvalContext._find_in_node(source, path, return_intermediate=True, include_names=False, allow_incomplete=True)
            for node in nodes:
                if node.yamlfigns.delete:
                    ret.append(i)
                    break

        return ret
