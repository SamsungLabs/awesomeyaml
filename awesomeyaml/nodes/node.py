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

from ..namespace import NamespaceableMeta, Namespace, staticproperty
from ..utils import persistent_id


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
        'merge_mode',
        'delete',
        'source_file',
        'dependencies',
        'users'
    ]

    _default_filename = threading.local()

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

    def __init__(self, idx=None, merge_mode=None, delete=None, metadata=None, source_file=None, implicit_delete=False):
        if merge_mode not in [None, 0, ConfigNode.WEAK, ConfigNode.FORCE]:
            raise ValueError(f'Unknown merge mode value: {merge_mode}')
        self._idx = idx
        self._merge_mode = merge_mode
        self._delete = delete
        self._implicit_delete = implicit_delete
        self._source_file = source_file if source_file is not None else getattr(ConfigNode._default_filename, 'value', None)
        self._metadata = metadata or {}

        self._default_merge_mode = ConfigNode.STANDARD
        self._default_delete = False

    def __repr__(self, simple=False):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x}>'

    class ayns(Namespace):
        @property
        def idx(self):
            return self._idx

        @property
        def merge_mode(self):
            if self._merge_mode is None:
                return self._default_merge_mode

            return self._merge_mode

        @property
        def weak(self):
            return self.ayns.merge_mode == ConfigNode.WEAK

        @property
        def force(self):
            return self.ayns.merge_mode == ConfigNode.FORCE

        @property
        def delete(self):
            if self._delete is None:
                if self._implicit_delete:
                    return True
                return self._default_delete

            return self._delete

        @property
        def explicit_delete(self):
            if self._delete is None:
                return self._default_delete
            return self._delete

        @property
        def source_file(self):
            return self._source_file

        @property
        def metadata(self):
            return self._metadata

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
            if self.ayns.merge_mode == other.ayns.merge_mode:
                return if_equal
            return self.ayns.merge_mode > other.ayns.merge_mode

        def preprocess(self, builder):
            return self.ayns.on_preprocess([], builder)

        def on_preprocess(self, path, builder):
            return self

        def premerge(self, into=None):
            return self.ayns.on_premerge([], into)

        def on_premerge(self, path, into):
            return self

        def evaluate(self):
            return self.ayns.evaluate_node([], self)

        def evaluate_node(self, path, root):
            evaluated = self.ayns.on_evaluate(path, root)
            assert evaluated is not self
            assert not isinstance(evaluated, ConfigNode)
            return evaluated

        def on_evaluate(self, path, ctx):
            return self.ayns.value

        def get_node_info_to_save(self):
            ''' This function should return a dict with values which one wants to preserve when dumping the node.
            '''
            # by default we don't care about node idx or source file (after dumping this will change anyway)
            # we care about custom metadata and "merge_mode" and "delete"
            # Note that "merge_mode" and "delete" might be optimized out from the dump output if
            # they would be set by the parent (dumping function holds a stack of which metadata are "default"
            # and does not produce anything which is aligned with the defaults)
            ret = copy.copy(self._metadata)
            ret['merge_mode'] = self._merge_mode
            ret['delete'] = self._delete #if not self._implicit_delete else None
            return ret

        @property
        def node_info(self):
            return {
                'idx': self._idx,
                'merge_mode': self._merge_mode,
                'delete': self._delete,
                'implicit_delete': self._implicit_delete,
                'source_file': self._source_file,
                'metadata': self._metadata
            }

        def get_default_mode(self):
            return {
                'merge_mode': self._default_merge_mode,
                'delete': self._default_delete
            }

        def represent(self):
            ''' Returns a tuple ``(tag, metadata, data)``, where ``tag`` is desired tag (can be ``None``),
                ``metadata`` is a dict with metadata (optional, can evaluate to ``False`` to ignore),
                and ``data`` is object which will be used to recursively represent ``self`` (can be either
                mapping, sequence or scalar).
            '''
            return self.ayns.tag, self.ayns.get_node_info_to_save(), self.ayns.value
