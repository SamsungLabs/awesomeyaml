import re
import collections

from .node import ConfigNode
from ..namespace import Namespace, staticproperty


class ComposedNode(ConfigNode):
    _path_component_regex = re.compile(r'''
                # the available options are:
                    (?:^|(?<=\.)) # ...if it is either at the beginning or preceded by a dot (do not capture)
                    ( [a-zA-Z0-9_]+ ) # a textual identifier (captured by the fist capture group)
                | # OR...
                    \[ (-?[0-9]+) \] # a (possibly negative) integer in [] (with second capture group catching the integer inside)
                | # OR...
                    (?<!^) # ... if it's not the first character ...
                    \. # a single dot
                    (?:(?!$)(?!\.)(?!\[)) # ... does not appear at the end and is not followed by either another dot or [ (do not capture)
                ''', re.VERBOSE) # verbose flag enables us to have comments, whitespace (inc. multi-line) etc. for better readability

    @staticmethod
    def split_path(path_str, validate=True):
        matches = ComposedNode._path_component_regex.finditer(path_str)
        if validate:
            _matches_cache = []
            beg = None
            end = None
            for match in matches:
                _matches_cache.append(match)
                if beg is None:
                    beg = match.start()
                # in the first iteration, check is beg (i.e. match.start()) == 0 to make sure we do not have an invalid prefix
                # in every other iteration make sure the new match strictly follow the previous one, if it doesn't that means
                # that there was an invalid part between them (invalid here means not matching our regular expression)
                if match.start() != (end if end is not None else 0):
                    raise ValueError(f'Invalid path: {path_str!r}')
                end = match.end()

            # the path is fine at the begining and internally doesn't have any "gaps" but has an incorrect suffix
            # (i.e. a part at the end which doesn't match our regular expression)
            if path_str and end != len(path_str):
                raise ValueError(f'Invalid path: {path_str!r}')

            matches = _matches_cache
        
        for match in matches:
            if match.group(1): # name
                yield str(match.group(1))
            elif match.group(2):  # index
                yield int(match.group(2))
            else:
                # sanity check
                assert match.group(0) == '.'

    @staticmethod
    def join_path(path_list):
        ret = ''
        for component in path_list:
            ret = ret + ComposedNode._get_child_accessor(component, ret)
        return ret

    @staticmethod
    def _get_child_accessor(childname, myname=''):
        if isinstance(childname, int):
            return f'[{childname}]'
        return ('.' if str(myname) else '') + str(childname)

    @staticmethod
    def get_list_path(*path, check_types=True):
        if not path:
            return []
        if len(path) == 1:
            if not isinstance(path[0], int):
                path = path[0]

        if path is None:
            return []
        if not isinstance(path, collections.Sequence) or isinstance(path, str):
            # split_path should only return str and ints so we don't need to check for types
            path = ComposedNode.split_path(str(path))
        elif check_types:
            for i, c in enumerate(path):
                # we need to check it because if something is not a string nor an int it's ambiguous which casting should be done
                if not isinstance(c, str) and (not isinstance(c, int) or isinstance(c, bool)):
                    raise ValueError(f'node path should be a list of ints and/or str only, got {type(c)} at position {i}: {c}')

        return path

    @staticmethod
    def get_str_path(*path, check_types=True):
        if not path:
            return ''
        if len(path) == 1:
            path = path[0]

        if path is None:
            return ''
        if isinstance(path, int):
            return ComposedNode._get_child_accessor(path)
        if isinstance(path, collections.Sequence) and not isinstance(path, str):
            return ComposedNode.split_path(path)

        if check_types and not isinstance(path, str):
            raise ValueError(f'Unexpected type: {type(path)}, expected int, sequence or str')
        return path

    def __init__(self, children, **kwargs):
        super().__init__(**kwargs)
        kwargs.pop('idx', None)
        kwargs.pop('metadata', None)
        kwargs.setdefault('_nodes_cache', {})
        kwargs.setdefault('_force_new', False)
        self._children = { name: ConfigNode(child, **kwargs) for name, child in children.items() }

    class node_info(Namespace):
        def set_child(self, name, value):
            value = ConfigNode(value)
            self._children[name] = value
            return value

        def remove_child(self, name):
            child = self._children.pop(name, None)
            return child

        def rename_child(self, old_name, new_name):
            if not self.node_info.has_child(old_name):
                raise ValueError(f'{self!r} does not have a child named: {old_name!r}')
            if self.node_info.has_child(new_name):
                raise ValueError(f'Cannot rename a child named: {old_name!r} to {new_name!r}, the new name is already assigned to another child')

            child = self._children[old_name]
            del self._children[old_name]
            self._children[new_name] = child
            return child

        def get_child(self, name, default=None):
            return self._children.get(name, default)

        def has_child(self, name):
            return name in self._children

        def get_node(self, *path, intermediate=False, names=False, incomplete=None):
            ''' Inputs:
                    - `path` either a list of names (str or int) which should be looked up, or a str equivalent to calling ComposedNode.join_path on an analogical list
                    - `intermediate` if True, returned is a list of nodes accessed (including self), in order of accessing, otherwise only the final node is returned (i.e. the last element of the list)
                    - `names` if True, returned are tuples of `(node, name, path)`, where `node` is an object represting a node with name `name` (relative to its parent) and path `path` (list of names, relative to the self),
                        otherwise only the node object is returned.
                        This option applies to both cases: with and without `intermediate` set to True - in both cases either the single value returned, or all the values in the returned list, are either tuples of single objects.
                        If `intermediate` is True, or `path` is empty list/None, `self` can be also returned in which case `name` is None and `path` is an empty list.
                    - `incomplete` if evaluates to True and a node with path `path` cannot be found, returns the first missing node as `None` (if `names` is False) or `(None, name, path)` - in case `intermediate` is also set to True,
                        the last element of the returned list will be the first missing node with the rest of the list populated as usual. If `incomplete` is `None` and the node doesn't exist, `None` is returned (`intermediate` and `names` are ignored in that case),
                        otherwise a `KeyError` is raised.

                Returns:
                    - a node found by following path `path`, optionally together with its name and the full path (if `names` is True), if the node exists,
                    - otherwise if `incomplete` is set to True, a node "found" is the first missing node and is returned as `None` (again, optionally with name and a full path),
                    - regardless of whether a node was found or None was used to indicated a missing node, if `intermediate` is set to True returned is a list of all nodes
                        which were accessed (in order of accessing) before the final node was reached - this includes `self`, also each node can be returned either on its own or as a tuple together with their names and paths

                Raises:
                    `KeyError` if node cannot be found and `incomplete` evaluates to False and is not None
            '''
            path = ComposedNode.get_list_path(*path)

            ret = []
            def _add(child, name):
                if names:
                    path = []
                    if ret:
                        path = ret[-1][2] + [name]
                    ret.append((child, name, path))
                else:
                    ret.append(child)
            
            _add(self, None)
            node = self
            found = True
            for component in path:
                if not isinstance(node, ComposedNode) or not node.node_info.has_child(component):
                    _add(None, component)
                    found = False
                    break

                node = node.node_info.get_child(component)
                _add(node, component)

            if not found and not incomplete:
                if incomplete is None:
                    return None

                raise KeyError(f'{ComposedNode.join_path(path)!r} does not exist within {self!r}')

            return ret if intermediate else ret[-1]

        def get_first_not_missing_node(self, *path, intermediate=False, names=False):
            def _get_node(n):
                return n if not names else n[0]
            nodes = self.node_info.get_node(*path, intermediate=True, names=names, incomplete=True)
            assert len(nodes) >= 2
            if _get_node(nodes[-1]) is not None:
                return nodes[-1] if not intermediate else nodes

            nodes.pop()
            assert _get_node(nodes[-1]) is not None
            return nodes[-1] if not intermediate else nodes

        def remove_node(self, *path):
            nodes = self.nodes_info.get_node(*path, intermediate=True, names=True, incomplete=None)
            if nodes is None:
                return None
            assert len(nodes) >= 2
            node, name, _ = nodes[-1]
            assert node is not None
            parent, _, _ = nodes[-2]
            return parent.node_info.remove_child(name)

        def filter_nodes(self, condition, prefix=None):
            prefix = prefix or []
            to_del = []
            for name, child in self.node_info.named_children():
                child_path = prefix + [name]
                keep = False
                if condition(child, child_path):
                    keep = True
                elif not child.node_info.is_leaf:
                    child.filter(condition, prefix=child_path)
                    keep = bool(child)

                if not keep:
                    to_del.append(name)

            for name in reversed(to_del):
                self.node_info.remove_child(name)

        def nodes_with_paths(self, prefix=None, recursive=True, include_self=True, allow_duplicates=True):
            memo = set()
            prefix = ComposedNode.get_list_path(prefix, check_types=False) or []
            if include_self:
                memo.add(id(self))
                yield prefix, self

            for name, child in self._children.items():
                if child is None or (id(child) in memo and not allow_duplicates):
                    continue
                child_path = prefix + [name]
                if not recursive or not isinstance(child, ComposedNode):
                    memo.add(id(child))
                    yield child_path, child
                else:
                    for path, node in child.node_info.nodes_with_paths(prefix=child_path, recursive=recursive, include_self=True):
                        if id(node) in memo and not allow_duplicates:
                            continue
                        memo.add(id(node))
                        yield path, node

        def nodes(self, recursive=True, include_self=True, allow_duplicates=False):
            for _, node in self.node_info.nodes_with_paths(recursive=recursive, include_self=include_self, allow_duplicates=allow_duplicates):
                yield node

        def named_children(self, allow_duplicates=True):
            memo = set()
            for name, child in self._children.items():
                if not allow_duplicates:
                    if id(child) in memo:
                        continue
                    memo.add(id(child))
                yield name, child

        def children(self, allow_duplicates=True):
            for _, child in self.node_info.named_children(allow_duplicates=allow_duplicates):
                yield child

        def children_count(self, allow_duplicates=True):
            if allow_duplicates:
                return len(self._children)
            else:
                return len(set(self._children.values()))

        def clear(self):
            self._children.clear()

        @staticproperty
        @staticmethod
        def is_leaf():
            return False

