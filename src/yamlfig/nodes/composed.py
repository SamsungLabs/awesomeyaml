import re

from .node import ConfigNode
from ..namespace import Namespace, staticproperty


class ComposedNode(ConfigNode):
    _path_component_regex = re.compile(r'''
                # the available options are:
                    (?:^|(?<=\.)) # ...if it is either at the beginning or preceeded by a dot (do not capture)
                    ( [a-zA-Z0-9_]+ ) # a textual indentifier (captured by the fist capture group)
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

            # the path is fine at the begining and internally doesn't have any "gaps" but has an incorect suffix
            # (i.e. a part at the end which doesn't match our regular expression)
            if end != len(path_str):
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

    def __init__(self, children, **kwargs):
        super().__init__(**kwargs)
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

        def get_node(self, path_str_or_list, intermediate=False, names=False, incomplete=None):
            ''' If at any point 
            '''
            name = None
            if not isinstance(path_str_or_list, list):
                name = str(path_str_or_list)
                path = ComposedNode.split_path(name)
            else:
                path = list(map(str, path_str_or_list))

            ret = []
            def _add(child, name):
                if names:
                    path = ''
                    if ret:
                        path = ret[-1][2] + ret[-1][0]._get_child_accessor(childname=name, myname=ret[-1][2])
                    ret.append((child, name, path))
                else:
                    ret.append(child)
            
            _add(self, '')
            node = self
            found = True
            for component in path:
                if not isinstance(node, ComposedNode):
                    _add(None, component)
                    break

                if not node.node_info.has_child(component):
                    try:
                        component = int(component)
                        if not node.node_info.has_child(component):
                            raise
                    except:
                        _add(None, component)
                        break

                node = node.node_info.get_child(component)
                _add(node, component)

            if not found and not incomplete:
                if incomplete is None:
                    return None

                raise KeyError(f'{name or ".".join(path)!r} does not exist within {self!r}')

            return ret if intermediate else ret[-1]


        def named_nodes(self, prefix='', recurse=True, include_self=True, allow_duplicates=True):
            memo = set()
            if include_self:
                memo.add(self)
                yield prefix, self

            for name, child in self._children.items():
                if child is None or (child in memo and not allow_duplicates):
                    continue
                child_name = prefix + self._get_child_accessor(name, myname=prefix)
                if not recurse:
                    memo.add(child)
                    yield child_name, child
                else:
                    for path, node in child.node_info.named_nodes(prefix=child_name, recurse=recurse, include_self=True):
                        if node in memo and not allow_duplicates:
                            continue
                        memo.add(node)
                        yield path, node

        def nodes(self, recurse=True, include_self=True, allow_duplicates=False):
            for _, node in self.node_info.named_nodes(recurse=recurse, include_self=include_self, allow_duplicates=allow_duplicates):
                yield node

        def named_children(self, allow_duplicates=True):
            memo = set()
            for name, child in self._children.items():
                if not allow_duplicates:
                    if child in memo:
                        continue
                    memo.add(child)
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

