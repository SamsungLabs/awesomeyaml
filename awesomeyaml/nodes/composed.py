# Copyright 2022 Samsung Electronics Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import collections.abc as cabc

from .node import ConfigNode
from ..namespace import Namespace, staticproperty
from ..utils import notnone_or


class NodePath(list):
    def __str__(self):
        return ComposedNode.get_str_path(self)

    def __repr__(self):
        return repr(self.__str__())

    def __add__(self, other):
        return NodePath(list.__add__(self, other))

    def __hash__(self):
        return hash(str(self))


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

            # the path is fine at the beginning and internally doesn't have any "gaps" but has an incorrect suffix
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
            return NodePath()
        if len(path) == 1:
            if not isinstance(path[0], int):
                path = path[0]

        if path is None:
            return NodePath()
        if not isinstance(path, cabc.Sequence) or isinstance(path, str):
            # split_path should only return str and ints so we don't need to check for types
            path = ComposedNode.split_path(str(path))
        elif check_types:
            for i, c in enumerate(path):
                # we need to check it because if something is not a string nor an int it's ambiguous which casting should be done
                if not isinstance(c, str) and (not isinstance(c, int) or isinstance(c, bool)):
                    raise ValueError(f'node path should be a list of ints and/or str only, got {type(c)} at position {i}: {c}')

        return NodePath(path)

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
        if isinstance(path, cabc.Sequence) and not isinstance(path, str):
            return ComposedNode.join_path(path)

        if check_types and not isinstance(path, str):
            raise ValueError(f'Unexpected type: {type(path)}, expected int, sequence or str')
        return path

    def _get_child_kwargs(self, child=None):
        ret = {}
        if not hasattr(self, '_delete'): # happens when unpickling! children are being populated before attributes are set, but its ok since we assume pickled objects are ok anyway, so no need to fix things
            return ret
        ret['implicit_delete'] = notnone_or(self._delete, self._default_delete or self._implicit_delete)
        ret['implicit_allow_new'] = notnone_or(self._allow_new, self._implicit_allow_new)
        if child is None or getattr(child, '_implicit_safe') is not False: # do not set "implicit_safe" arg if the child exists and already has it set to False (note: I think it's not strictly necessary to handle it here since other checks would still prevent changes)
            ret['implicit_safe'] = notnone_or(self._safe, self._implicit_safe)
        return ret

    def _propagate_implicit_values(self):
        if not hasattr(self, '_delete'): # happens when unpickling! children are being populated before attributes are set, but its ok since we assume pickled objects are ok anyway, so no need to fix things
            return
        if self._implicit_delete is None and self._implicit_allow_new is None and self._implicit_safe is None:
            return
        if self._delete is not None and self._allow_new is not None and self._safe is not None:
            return

        for child in self._children.values():
            fix = False
            if self._delete is None:
                if child._implicit_delete != self._implicit_delete:
                    child._implicit_delete = self._implicit_delete
                    fix = True
            if self._allow_new is None:
                if child._implicit_allow_new != self._implicit_allow_new:
                    child._implicit_allow_new = self._implicit_allow_new
                    fix = True
            if self._safe is None:
                if child._implicit_safe != self._implicit_safe:
                    if child._implicit_safe is not False:
                        child._implicit_safe = self._implicit_safe
                        fix = True

            if fix:
                child._propagate_implicit_values()

    def __init__(self, children, nodes_memo=None, **kwargs):
        super().__init__(**kwargs)
        kwargs.pop('idx', None)
        kwargs.pop('metadata', None)
        kwargs.pop('delete', None)
        kwargs.pop('allow_new', None)
        kwargs.pop('safe', None)
        kwargs.update(self._get_child_kwargs())
        nodes_memo = nodes_memo if nodes_memo is not None else {}
        self._children = { name: ConfigNode(child, **kwargs, nodes_memo=nodes_memo) for name, child in children.items() } # pylint: disable=unexpected-keyword-arg

    class ayns(Namespace):
        def set_child(self, name, value):
            value = ConfigNode(value, **self._get_child_kwargs())
            self._children[name] = value
            value._propagate_implicit_values()
            return value

        def remove_child(self, name):
            child = self._children.pop(name, None)
            return child

        def rename_child(self, old_name, new_name):
            if not self.ayns.has_child(old_name):
                raise ValueError(f'{self!r} does not have a child named: {old_name!r}')
            if self.ayns.has_child(new_name):
                raise ValueError(f'Cannot rename a child named: {old_name!r} to {new_name!r}, the new name is already assigned to another child')

            child = self._children[old_name]
            del self._children[old_name]
            self._children[new_name] = child
            return child

        def get_child(self, name, default=None):
            return self._children.get(name, default)

        def has_child(self, name):
            if '_children' not in self.__dict__:
                return False
            return name in self._children

        @staticmethod
        def _get_node(root, access_fn, query_fn, *path, intermediate=False, names=False, incomplete=None):
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

            _add(root, None)
            node = root
            found = True
            for component in path:
                if not query_fn(node, component): #not isinstance(node, ComposedNode) or not node.ayns.has_child(component):
                    _add(None, component)
                    found = False
                    break

                #node = node.ayns.get_child(component)
                node = access_fn(node, component)
                _add(node, component)

            if not found and not incomplete:
                if incomplete is None:
                    return None

                raise KeyError(f'{ComposedNode.join_path(path)!r} does not exist within {root!r}')

            return ret if intermediate else ret[-1]

        @staticmethod
        def _remove_node(root, remove_fn, *path):
            nodes = root.ayns.get_node(*path, intermediate=True, names=True, incomplete=None)
            if nodes is None:
                return None
            if len(nodes) == 1:
                raise ValueError(f'Cannot remove self from self')
            assert len(nodes) >= 2
            node, name, _ = nodes[-1]
            assert node is not None
            parent, _, _ = nodes[-2]
            return remove_fn(parent, name)

        def get_node(self, *path, intermediate=False, names=False, incomplete=False):
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
            def access_fn(node, component):
                return node.ayns.get_child(component)
            def query_fn(node, component):
                if not isinstance(node, ComposedNode):
                    return False
                return node.ayns.has_child(component)

            return ComposedNode.ayns._get_node(self, access_fn, query_fn, *path, intermediate=intermediate, names=names, incomplete=incomplete)

        def get_first_not_missing_node(self, *path, intermediate=False, names=False):
            def _get_node(n):
                return n if not names else n[0]
            nodes = self.ayns.get_node(*path, intermediate=True, names=names, incomplete=True)
            assert len(nodes) >= 2 or nodes[-1] is self
            if _get_node(nodes[-1]) is not None:
                return nodes[-1] if not intermediate else nodes

            nodes.pop()
            assert _get_node(nodes[-1]) is not None
            return nodes[-1] if not intermediate else nodes

        def remove_node(self, *path):
            def remove_fn(node, component):
                return node.ayns.remove_child(component)

            return ComposedNode.ayns._remove_node(self, remove_fn, *path)

        def replace_node(self, new_node, *path):
            raise NotImplementedError()

        def filter_nodes(self, condition, prefix=None, removed=None):
            prefix = ComposedNode.get_list_path(prefix, check_types=False) or NodePath()
            to_del = []
            to_re_set = []
            for name, child in self.ayns.named_children():
                child_path = prefix + [name]
                keep = False
                if condition(child_path, child):
                    keep = True
                if isinstance(child, ComposedNode): #not child.ayns.is_leaf:
                    possibly_new_child = child.ayns.filter_nodes(condition, prefix=child_path, removed=removed)
                    keep = keep or bool(possibly_new_child)
                    if keep and possibly_new_child is not child:
                        to_re_set.append(name, possibly_new_child)

                if not keep:
                    to_del.append(name)

            for name in reversed(to_del):
                self.ayns.remove_child(name)
                if removed is not None:
                    removed.add(prefix + [name])
            for name, child in to_re_set:
                self.ayns.set_child(name, child)

            return self

        def map_nodes(self, map_fn, prefix=None, cache_results=True, cache=None, leafs_only=True):
            prefix = ComposedNode.get_list_path(prefix, check_types=False) or NodePath()
            to_re_set = []
            if cache_results and cache is None:
                cache = {}

            for name, child in self.ayns.named_children():
                if cache_results and id(child) in cache:
                    possibly_new_child = cache[id(child)]
                else:
                    child_path = prefix + [name]
                    possibly_new_child = child
                    if isinstance(child, ComposedNode):
                        possibly_new_child = possibly_new_child.ayns.map_nodes(map_fn, prefix=child_path, cache_results=cache_results, cache=cache, leafs_only=leafs_only)
                    else:
                        possibly_new_child = map_fn(child_path, possibly_new_child)
                        
                if possibly_new_child is not child:
                    to_re_set.append((name, possibly_new_child))

                if cache_results:
                    from ..utils import persistent_id
                    cache[persistent_id(child)] = possibly_new_child

            for name, child in to_re_set:
                self.ayns.set_child(name, child)

            ret = self
            if not leafs_only:
                ret = map_fn(prefix, self)

            return ret

        def nodes_with_paths(self, prefix=None, recursive=True, include_self=False, allow_duplicates=True):
            memo = set()
            prefix = ComposedNode.get_list_path(prefix, check_types=False) or NodePath()
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
                    for path, node in child.ayns.nodes_with_paths(prefix=child_path, recursive=recursive, include_self=True):
                        if id(node) in memo and not allow_duplicates:
                            continue
                        memo.add(id(node))
                        yield path, node

        def nodes(self, recursive=True, include_self=False, allow_duplicates=False):
            for _, node in self.ayns.nodes_with_paths(recursive=recursive, include_self=include_self, allow_duplicates=allow_duplicates):
                yield node

        def nodes_paths(self, prefix=None, recursive=True, include_self=False):
            for path, _ in self.ayns.nodes_with_paths(recursive=recursive, include_self=include_self, allow_duplicates=True):
                yield path


        def named_children(self, allow_duplicates=True):
            memo = set()
            for name, child in self._children.items():
                if not allow_duplicates:
                    if id(child) in memo:
                        continue
                    memo.add(id(child))
                yield name, child

        def children(self, allow_duplicates=True):
            for _, child in self.ayns.named_children(allow_duplicates=allow_duplicates):
                yield child

        def children_names(self):
            for key in self._children.keys():
                yield key

        def children_count(self, allow_duplicates=True):
            if allow_duplicates:
                return len(self._children)
            else:
                return len(set(self._children.values()))

        def clear(self):
            self._children.clear()

        def preprocess(self, builder):
            return self.ayns.map_nodes(lambda path, node: node.ayns.on_preprocess(path, builder), cache_results=True, leafs_only=False)

        def premerge(self, into=None):
            return self.ayns.map_nodes(lambda path, node: node.ayns.on_premerge(path, into), cache_results=True, leafs_only=False)

        def nested_merge(self, other, prefix):
            if other.ayns.delete:
                removed = set()
                def maybe_keep(path, node):
                    other_node = other.ayns.get_first_not_missing_node(path)
                    return node.ayns.has_priority_over(other_node)

                self.ayns.filter_nodes(maybe_keep, prefix=prefix, removed=removed)
                if not self._children and other.ayns.has_priority_over(self, if_equal=True):
                    removed.add(prefix)
                    other.ayns._require_all_new(prefix, f'note: the entire config tree under {prefix!r} has been removed due to node merging with a !del node', exceptions=removed)
                    return other

            _this_path = ComposedNode.get_str_path(prefix)
            if not _this_path:
                _this_path = '<top-level node>'

            for key, value in other._children.items():
                child = self.ayns.get_child(key, None)
                if child is None:
                    value.ayns._require_all_new(prefix + [key], f'last parent: {_this_path!r}, from file: {self.ayns.source_file!r}')
                    self.ayns.set_child(key, value)
                else:
                    merge = False
                    try:
                        possibly_new_child = child.ayns.nested_merge(value, prefix=prefix + [key])
                        merge = True
                    except (TypeError, AttributeError):
                        pass

                    if merge:
                        if not possibly_new_child and not possibly_new_child.ayns.has_priority_over(value) and value.ayns.explicit_delete:
                            self.ayns.remove_child(key)
                        elif possibly_new_child is not child:
                            self.ayns.set_child(key, possibly_new_child)
                            possibly_new_child._metadata = { **child._metadata, **possibly_new_child._metadata }
                    else:
                        value.ayns._require_all_new(prefix + [key], f'last parent: {_this_path!r}, from file: {self.ayns.source_file!r}', include_self=False)
                        if value.ayns.has_priority_over(child, if_equal=True):
                            if not value and value.ayns.explicit_delete:
                                self.ayns.remove_child(key)
                            else:
                                self.ayns.set_child(key, value)
                                value._metadata = { **child._metadata, **value._metadata }

            if other.ayns.has_priority_over(self, if_equal=True):
                self._priority = other._priority
                self._delete = other._delete
                self._implicit_delete = other._implicit_delete
                self._metadata = { **self._metadata, **other._metadata }
            else:
                self._metadata = { **other._metadata, **self._metadata }

            return self

        def merge(self, other):
            other.ayns.premerge(self)
            return self.ayns.nested_merge(other, prefix=NodePath())

        @staticproperty
        @staticmethod
        def is_leaf():
            return False

        def _require_all_new(self, path, reason, exceptions=None, include_self=True):
            seq = self.ayns.nodes_with_paths(prefix=path, include_self=include_self)
            for p, n in seq:
                if not n.ayns.allow_new and (exceptions is None or p not in exceptions):
                    raise ValueError(f'Node {p!r} (source file: {n.ayns.source_file!r}) requires that the destination already exists but the current config tree does not contain a node under this path ({reason})')


    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_children']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    @staticmethod
    def _recreate(cls):
        new = cls.__new__(cls)
        new._children = {}
        return new

    def __reduce__(self):
        state = self.__getstate__()
        lit = None
        dit = None
        if isinstance(self, list):
            lit = iter(self)
        elif isinstance(self, dict):
            dit = iter(self.items())
        return ComposedNode._recreate, (type(self), ), state, lit, dit
