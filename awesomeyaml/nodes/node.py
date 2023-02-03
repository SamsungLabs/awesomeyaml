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

import copy
import threading
import contextlib
import collections.abc as cabc

from .node_path import NodePath
from ..namespace import NamespaceableMeta, Namespace, staticproperty
from ..utils import persistent_id, notnone_or
from ..import errors


_kwargs_to_inherit = [
    'priority',
    'implicit_delete',
    'implicit_allow_new',
    'implicit_safe',
    'pyyaml_node'
]


def decorator_factory(error_type):
    def decorator(func):
        def impl(*args, **kwargs):
            self = args[0]
            path = args[1] if len(args) > 1 else kwargs['path']
            other = args[2] if len(args) > 2 else kwargs.get('other', None)
            if not isinstance(other, ConfigNode):
                other = None
            with errors.rethrow(error_type, self, path, other):
                return func(*args, **kwargs)

        return impl
    return decorator


rethrow_as_preprocess_error = decorator_factory(errors.PreprocessError)
rethrow_as_premerge_error = decorator_factory(errors.PremergeError)
rethrow_as_merge_error = decorator_factory(errors.MergeError)
rethrow_as_eval_error = decorator_factory(errors.EvalError)


class ConfigNodeMeta(NamespaceableMeta):
    def __call__(cls,
            *args,
            nodes_memo=None,
            _force_type=False,
            **kwargs):
        value = None
        has_value = False
        if args:
            value = args[0]
            args = args[1:]
            has_value = True

        # check if type deduction is required
        if cls is ConfigNode and not _force_type:
            # deduce type and call it recursively (this time enforcing it)
            if not has_value:
                raise ValueError('Cannot deduce target type without a positional argument - deduction is always done w.r.t. the first argument')
            if isinstance(value, ConfigNode):
                for arg_name in _kwargs_to_inherit:
                    if arg_name in kwargs:
                        # do not change implicit_safe if already set to False
                        if arg_name == 'implicit_safe' and getattr(value, '_' + arg_name) is False:
                            del kwargs[arg_name]
                            continue
                        setattr(value, '_' + arg_name, kwargs[arg_name])
                if any(k.startswith('implicit_') for k in kwargs.keys()):
                    value._propagate_implicit_values()

                return value
            else:
                from .dict import ConfigDict
                from .list import ConfigList
                from .tuple import ConfigTuple
                from .scalar import ConfigScalar

                if isinstance(value, cabc.Sequence) and not isinstance(value, str) and not isinstance(value, bytes):
                    if isinstance(value, cabc.MutableSequence):
                        t = ConfigList
                    else:
                        t = ConfigTuple
                elif isinstance(value, cabc.MutableMapping):
                    t = ConfigDict
                else:
                    t = ConfigScalar

            # dispatch actual object creation (see below)
            # we need to do that recursively since __call__ method can be overwritten (e.g. ConfigScalar)
            return t(value, *args, nodes_memo=nodes_memo, _force_type=True, **kwargs)

        # actual object creation
        if has_value and nodes_memo is not None and id(value) in nodes_memo:
            return nodes_memo[id(value)]

        from .composed import ComposedNode
        if issubclass(cls, ComposedNode):
            kwargs['nodes_memo'] = nodes_memo

        if has_value:
            ret = NamespaceableMeta.__call__(cls, value, *args, **kwargs)
        else:
            assert not args
            ret = NamespaceableMeta.__call__(cls, **kwargs)

        if has_value and nodes_memo is not None:
            assert id(value) not in nodes_memo
            nodes_memo[persistent_id(value)] = ret

        return ret


class ConfigNode(metaclass=ConfigNodeMeta):
    WEAK = -1
    STANDARD = 0
    FORCE = 1

    special_metadata_names = [
        'idx',
        'priority',
        'delete',
        'allow_new',
        'source_file',
        'safe'
    ]

    _default_filename = threading.local()
    _default_safe = threading.local()
    _default_priority = STANDARD
    _default_delete = False
    _default_allow_new = True

    @staticmethod
    @contextlib.contextmanager
    def default_filename(filename):
        if not hasattr(ConfigNode._default_filename, 'value'):
            ConfigNode._default_filename.value = None

        old = ConfigNode._default_filename.value
        ConfigNode._default_filename.value = filename
        try:
            yield
        finally:
            ConfigNode._default_filename.value = old

    @staticmethod
    @contextlib.contextmanager
    def default_safe_flag(value):
        if not hasattr(ConfigNode._default_safe, 'value'):
            ConfigNode._default_safe.value = True

        old = ConfigNode._default_safe.value
        ConfigNode._default_safe.value = value and old
        try:
            yield
        finally:
            ConfigNode._default_safe.value = old


    def __init__(self, idx=None, priority=None, delete=None, allow_new=None, safe=None, metadata=None, source_file=None, implicit_delete=None, implicit_allow_new=None, implicit_safe=None, pyyaml_node=None):
        ''' '''

        """ There's a lit bit going on with merging flags here, basically the main idea is that we have 3 sources of flags, they are (in the precedence order):
                 - explicit merging-controlling information attached to this node (highest precedence), this are passed as "delete", "allow_new", etc.
                 - merging flags inherited from a parent node (aka implicit flags) - these can only have not-None value if there's an ancestor node with explicit flag, however the immediate parent does not have to have a flag specified explicitly
                 - a node type's defaults
        """
        if priority not in [None, ConfigNode.STANDARD, ConfigNode.WEAK, ConfigNode.FORCE]:
            raise ValueError(f'Unknown priority value: {priority}')
        self._idx = idx
        self._priority = priority
        self._delete = delete
        self._allow_new = allow_new
        self._implicit_delete = implicit_delete
        self._implicit_allow_new = implicit_allow_new
        self._source_file = source_file if source_file is not None else getattr(ConfigNode._default_filename, 'value', None)
        self._metadata = metadata or {}
        self._pyyaml_node = pyyaml_node
        self._safe = safe
        self._implicit_safe = implicit_safe
        self._default_safe = getattr(ConfigNode._default_safe, 'value', False)

    def __repr__(self, simple=False):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x}>'

    class ayns(Namespace):
        @property
        def idx(self):
            return self._idx

        @property
        def priority(self):
            if self._priority is None:
                return self._default_priority

            return self._priority

        @property
        def weak(self):
            return self.ayns.priority == ConfigNode.WEAK

        @property
        def force(self):
            return self.ayns.priority == ConfigNode.FORCE

        @property
        def delete(self):
            if self._delete is None:
                if self._implicit_delete is not None:
                    return self._implicit_delete
                return self._default_delete

            return self._delete

        @property
        def allow_new(self):
            if self._implicit_allow_new is not None:
                return self._implicit_allow_new
            return self._default_allow_new

        @property
        def explicit_delete(self):
            return self._delete

        @property
        def source_file(self):
            return self._source_file

        @property
        def metadata(self):
            return self._metadata

        @property
        def safe(self):
            return notnone_or(self._safe, True) and notnone_or(self._implicit_safe, True) and notnone_or(self._default_safe, False)

        @staticproperty
        @staticmethod
        def is_leaf():
            return True

        @staticproperty
        @staticmethod
        def is_root():
            return False

        @property
        def value(self):
            return self._get_value()

        @property
        def native_value(self):
            return self._get_native_value()

        @value.setter
        def value(self, value):
            return self._set_value(value)

        @staticproperty
        @staticmethod
        def tag():
            return None

        def has_priority_over(self, other, if_equal=False):
            if self.ayns.priority == other.ayns.priority:
                return if_equal
            return self.ayns.priority > other.ayns.priority


        #
        # The following functions follow a high-level naming conention as follows:
        #   - <name> - is a top level method that should be called on the top-level config objects only
        #   - on_<name> - is an equivalent that is being called recursively for all nodes in the config object when <name> is called
        #   - on_<name>_impl - is the part of "on_<name>" that can/should be overwritten by derived classes - it should always be called indirectly via "on_<name>"
        #
        # Note: "evaluate" does not exist as it is implemented in EvalContext (since we need to keep state in a separate class) - we could have "evaluate" here
        # and delegate functionality to the EvalContext but to prevent possible errors it's better to remove it altogether (e.g., to avoid accidental recursive calls)

        def preprocess(self, builder):
            return self.ayns.on_preprocess(NodePath(), builder)

        @rethrow_as_preprocess_error
        def on_preprocess(self, path, builder):
            return self.ayns.on_preprocess_impl(path, builder)

        def on_preprocess_impl(self, path, builder):
            return self


        def premerge(self, into=None):
            return self.ayns.on_premerge(NodePath(), into)

        @rethrow_as_premerge_error
        def on_premerge(self, path, into):
            return self.ayns.on_premerge_impl(path, into)

        def on_premerge_impl(self, path, into):
            return self


        def merge(self, other):
            if other is None:
                if not self.ayns.allow_new:
                    raise ValueError('A top-level destination node does not exist but this top-level node has a !notnew flag enabled!')
                return self

            other.ayns.premerge(self)
            return self.ayns.on_merge(NodePath(), other)

        @rethrow_as_merge_error
        def on_merge(self, path, other):
            return self.ayns.on_merge_impl(path, other)

        def on_merge_impl(self, path, other):
            if self.ayns.has_priority_over(other):
                self._replace_other(other, allow_promotions=False)
                return self
            other._replace_other(self, allow_promotions=False)
            return other


        @rethrow_as_eval_error
        def on_evaluate(self, path, root):
            evaluated = self.ayns.on_evaluate_impl(path, root)
            assert evaluated is not self
            assert not isinstance(evaluated, ConfigNode)
            return evaluated

        def on_evaluate_impl(self, path, ctx):
            return self.ayns.value


        def get_node_info_to_save(self):
            ''' This function should return a dict with values which one wants to preserve when dumping the node.
            '''
            # by default we don't care about node idx or source file (after dumping this will change anyway)
            # we care about custom metadata and "priority" and "delete"
            # Note that "priority" and "delete" might be optimized out from the dump output if
            # they would be set by the parent (dumping function holds a stack of which metadata are "default"
            # and does not produce anything which is aligned with the defaults)
            ret = copy.copy(self._metadata)
            ret['priority'] = self._priority
            ret['delete'] = self._delete #if not self._implicit_delete else None
            ret['allow_new'] = self._allow_new
            ret['safe'] = self._safe
            return ret

        @property
        def node_info(self):
            return {
                'idx': self._idx,
                'priority': self._priority,
                'delete': self._delete,
                'implicit_delete': self._implicit_delete,
                'allow_new': self._allow_new,
                'implicit_allow_new': self._implicit_allow_new,
                'safe': self._safe,
                'implicit_safe': self._implicit_safe,
                'default_safe': self._default_safe,
                'source_file': self._source_file,
                'metadata': self._metadata
            }

        def get_default_mode(self):
            return {
                'priority': self._default_priority,
                'delete': self._default_delete,
                'allow_new': self._default_allow_new,
                'safe': self._default_safe
            }

        def represent(self):
            ''' Returns a tuple ``(tag, metadata, data)``, where ``tag`` is desired tag (can be ``None``),
                ``metadata`` is a dict with metadata (optional, can evaluate to ``False`` to ignore),
                and ``data`` is object which will be used to recursively represent ``self`` (can be either
                mapping, sequence or scalar).
            '''
            return self.ayns.tag, self.ayns.get_node_info_to_save(), self.ayns.value

        def _require_all_new(self, path, reason, exceptions=None, include_self=True):
            if not include_self:
                return
            if not self.ayns.allow_new and (exceptions is None or path not in exceptions):
                raise ValueError(f'Node {path!r} (source file: {self._source_file!r}) requires that the destination already exists but the current config tree does not contain a node under this path ({reason})')

        def _require_safe(self, path):
            if not self.ayns.safe:
                raise errors.UnsafeError(None, self, path)

    def _propagate_implicit_values(self):
        return

    #
    # The following methods are used to implement some core merging semantics - they are intended to be called whenever two nodes are merged.
    # Depending on the desired outcome, if we are merging nodes "A <- B", one of the four possible outcomes should happen:
    #   - if B has higher priority than A and we want to use B's memory location to store the output, one should call "B._replace_other(A)"
    #   - if B has higher priority than A but we want to use A's memory location to store the output, one should call "A._replace_self(B)"
    #   - if B has lower priority and we want to use B to store the result, "B._replace_self(A)" should be called
    #   - finally, if B has lower priority and A is to be used to hold the result, "A._replace_other(B)" should be called
    #
    # In summary, the generic rule: "<resulting_node_obj>._replace_{self|other}(<other_node_obj>)" where <resulting_node_obj> is the object
    # that is intended to be returned by the merging method and "{self|other}" depends on the relative priority between the two nodes.
    #
    # These methods >> DO NOT << handle the logic to perform merging of the nodes' content, it is assumed that the "<resulting_node_obj>" already
    # holds correct content - which is the result of the merge - at the moment of calling these methods.
    # However, the methods might still modify some class-specific content via promotion mechanism (conditioned on the relevant argument).
    # Promotion happen when merging "A <- B" and one of the nodes has more specific type than the other, e.g., A is "!bind" node
    # and B is a dict with "!del" - in such a case, it can happen that B is going to be the result of the merge (if the entire subtree under node A
    # is deleted), but that would make the resulting type to be "dict", rather than "!bind". To ensure correct behaviour, promotion mechanism will
    # attempt to promote the "!bind" node to be the result rather than "dict" by moving the entire content of the dict node into the "!bind" and
    # returning the latter. Therefore the final result is equivalent to returning "dict" but with extra elements specific to the "!bind" node.
    #

    def _replace_self(self, other, allow_promotions=False):
        ''' Helper that should be called whenever "other" is merged into "self" with higher priority,
            but we want to keep the resulting object inside the memory of "self".

            Intuitively speaking, it will try to make "self" look like "other".
        '''
        self._priority = other._priority
        self._delete = other._delete
        if other._safe is not None:
            self._safe = notnone_or(self._safe, True) and other._safe
        if other._default_safe is not None:
            self._default_safe = notnone_or(other._default_safe, True) and other._default_safe
        self._metadata = { **self._metadata, **other._metadata }
        if allow_promotions:
            ret = self._maybe_promote(other)
        else:
            ret = self
        ret._propagate_implicit_values()
        return ret

    def _replace_other(self, other, allow_promotions=False):
        ''' Helper that should be called whenever "other" is merged into "self" with lower priority,
            and we want to keep "self" as the resulting node (subject to promotions).

            Intuitively speaking, it will selectively add content of "other" into "self" to make sure that
            any extra information is preserved, while keeping the content already present in "self" as it is.

            If "allow_promotions" is set to True, "other" can be returned instead of "self" if its type is preferred.
            In such case, its content will be identical to the content of "self" after replacement has been done,
            with any extra content coming from other's type preserved.
        '''
        if other._safe is not None:
            self._safe = notnone_or(self._safe, True) and other._safe
        if other._default_safe is not None:
            self._default_safe = notnone_or(other._default_safe, True) and other._default_safe
        self._metadata = { **other._metadata, **self._metadata }
        if allow_promotions:
            return self._maybe_promote(other)
        return self

    def _maybe_promote(self, other):
        ''' Possibly promote "other" to be returned rather than "self" if its type is preferred.

            This function >> DOES NOT << raise any errors related to types, i.e., it assumes all checks have already
            been made and a correct merge is FINISHING, with the last step being promoting types, if needed. Consequently,
            if promotion is not possible, the method WILL NOT REPORT any errors, instead will simply give up.

            Argument convention is that "self" is about to replace "other" as the result of merging.

            If "other" is promoted, it should replicate "self" as much as possible.
        '''
        if type(self) is type(other):
            return self
        if not self._is_composed() or not other._is_composed():
            return self

        if issubclass(type(other), type(self)): # simple case, plain dict/list replaces complex dict/list, promote complex
            other.clear()
            if isinstance(other, list):
                other.extend(self)
            else:
                other.update(self)
            other.__dict__.update(self.__dict__)
            return other
        elif issubclass(type(self), type(other)): # complex dict/list replaces simple dict/list, leave as is
            return self
        elif self._is_plain_composed() and not other._is_plain_composed():  # plain dict/list replaces complex list/dict, promote complex
            other.clear()
            if isinstance(other, list):
                other.extend(self.values())
            else:
                other.update(enumerate(self))
            other.__dict__.update(self.__dict__)
            return other
        elif not self._is_plain_composed() and other._is_plain_composed(): # complex dict/list replaces simple list/dict, leave as is
            return self
        else: # any other case, silently give up
            return self

    @classmethod
    def _is_composed(cls):
        return False

    @classmethod
    def _is_plain_composed(cls):
        return False
