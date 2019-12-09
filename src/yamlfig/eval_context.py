import functools

from .nodes.composed import ComposedNode
from .nodes.delete import DelNode


class EvalContext():
    def __init__(self, sources):
        self.sources = tuple(sources)

    def get_node(self, name):
        if not self.sources:
            return None
        if len(self.sources) == 1:
            return self._find_in_node(self.sources[0], name, return_intermediate=False, include_names=False, allow_incomplete=None)

        candidate = None
        start = None

        candidate, index = self.rfind(name, start=None, return_intermediate=True, include_names=True)
        start = index - 1

        # Check for 'weak' and 'force'
        while not candidate[-1][1].node_info.force:
            try:
                override, index2 = self.rfind(name, start=start, return_intermediate=True, include_names=True)
                start = index2 - 1
                if (candidate[-1][1].node_info.weak and not override[-1][1].node_info.weak) or (not candidate[-1][1].node_info.force and override[-1][1].node_info.force):
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
                if node.node_info.delete:
                    ret.append(i)
                    break

        return ret


    def find(self, name, stop=None, start=None, return_intermediate=False, include_names=False):
        if start is None:
            start = 0
        if stop is None:
            stop = len(self.sources)
        return self._find(name, start=start, stop=stop, rev=False, return_intermediate=return_intermediate, include_names=include_names)

    def rfind(self, name, stop=None, start=None, return_intermediate=False, include_names=False):
        if start is None:
            start = len(self.sources) - 1
        if stop is None:
            stop = -1
        return self._find(name, start=start, stop=stop, rev=True, return_intermediate=return_intermediate, include_names=include_names)

    def _find(self, name, start, stop, rev, return_intermediate, include_names):
        path = EvalContext.split_name(name)
        srcs = enumerate(self.sources)
        if rev:
            start = len(self.sources) - start - 1
            stop = len(self.sources) - stop + 1
            srcs = reversed(srcs)

        for i, source in srcs[start:stop]:
            try:
                return EvalContext._find_in_node(source, path, return_intermediate=return_intermediate, include_names=include_names, allow_incomplete=False), i
            except KeyError:
                pass

        raise KeyError(f'{name!r} does not exist in in the evaluation context')

    @staticmethod
    def _find_in_node(node, name, return_intermediate, include_names, allow_incomplete):
        if isinstance(name, str):
            path = EvalContext.split_name(name)
        else:
            path = name
            name = None

        ret = []
        def _add(child, name):
            if include_names:
                path = ''
                if ret:
                    path = ret[-1][2] + ret[-1][0]._get_child_accessor(childname=name, myname=ret[-1][2])
                ret.append((child, name, path))
            else:
                ret.append(child)

        _add(node, '')
        found = True
        for component in path:
            if not isinstance(node, ComposedNode):
                found = False
                break
            if not node.has_child(component):
                found = False
                break

            node = node.get_child(component)
            _add(node, component)

        if not found and not allow_incomplete:
            if allow_incomplete is None:
                return None

            if name is None:
                name = '.'.join(path)
            raise KeyError(f'{name!r} does not exist within {node!r}')

        if not return_intermediate:
            return ret[-1]
        
        return ret
