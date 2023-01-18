import re
import collections.abc as cabc


class NodePath(list):
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

    def __str__(self):
        return self.get_str_path(self)

    def __repr__(self):
        return repr(self.__str__())

    def __add__(self, other):
        return NodePath(list.__add__(self, other))

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def split_path(cls, path_str, validate=True):
        matches = cls._path_component_regex.finditer(path_str)
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

    @classmethod
    def join_path(cls, path_list):
        ret = ''
        for component in path_list:
            ret = ret + cls._get_child_accessor(component, ret)
        return ret

    @classmethod
    def _get_child_accessor(cls, childname, myname=''):
        if isinstance(childname, int):
            return f'[{childname}]'
        return ('.' if str(myname) else '') + str(childname)

    @classmethod
    def get_list_path(cls, *path, check_types=True):
        if not path:
            return NodePath()
        if len(path) == 1:
            if not isinstance(path[0], int):
                path = path[0]

        if path is None:
            return NodePath()
        if not isinstance(path, cabc.Sequence) or isinstance(path, str):
            # split_path should only return str and ints so we don't need to check for types
            path = cls.split_path(str(path))
        elif check_types:
            for i, c in enumerate(path):
                # we need to check it because if something is not a string nor an int it's ambiguous which casting should be done
                if not isinstance(c, str) and (not isinstance(c, int) or isinstance(c, bool)):
                    raise ValueError(f'node path should be a list of ints and/or str only, got {type(c)} at position {i}: {c}')

        return NodePath(path)

    @classmethod
    def get_str_path(cls, *path, check_types=True):
        if not path:
            return ''
        if len(path) == 1:
            path = path[0]

        if path is None:
            return ''
        if isinstance(path, int):
            return cls._get_child_accessor(path)
        if isinstance(path, cabc.Sequence) and not isinstance(path, str):
            return cls.join_path(path)

        if check_types and not isinstance(path, str):
            raise ValueError(f'Unexpected type: {type(path)}, expected int, sequence or str')
        return path
