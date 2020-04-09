import copy
import threading
import contextlib
import collections

from ..namespace import NamespaceableMeta, Namespace, staticproperty
from ..utils import persistent_id


class ConfigNodeMeta(NamespaceableMeta):
    def __call__(cls,
            *args,
            _force_type=False,
            _nodes_cache=None,
            _cache_nodes=True,
            _force_new=False,
            _deep_new=False,
            _copy_guard=False,
            **kwargs):
        value = None
        has_value = False
        if args:
            value = args[0]
            args = args[1:]
            has_value = True

        if has_value and _cache_nodes and _nodes_cache is not None and id(value) in _nodes_cache:
            return _nodes_cache[id(value)]
        
        t = cls
        if isinstance(value, ConfigNode) and not _copy_guard:
            assert has_value
            if not _force_new:
                value._merge_mode = kwargs.get('merge_mode', value._merge_mode)
                value._delete = kwargs.get('merge_mode', value._delete)
                value._implicit_delete = kwargs.get('implicit_delete', value._implicit_delete)
                return value

            kwargs = dict(kwargs)
            kwargs['idx'] = value._idx
            kwargs['merge_mode'] = value._merge_mode
            kwargs['delete'] = value._delete
            kwargs['metadata'] = copy.deepcopy(value._metadata)
            kwargs['source_file'] = value._source_file
            kwargs['implicit_delete'] = value._implicit_delete

            # kwargs.setdefault('idx', value._idx)
            # kwargs.setdefault('merge_mode', value._merge_mode)
            # kwargs.setdefault('delete', value._delete)
            # kwargs.setdefault('metadata', copy.deepcopy(value._metadata))
            # kwargs.setdefault('source_file', value._source_file)
            # kwargs.setdefault('implicit_delete', value._implicit_delete)

            t = type(value)
            value = value.yamlfigns.value
            return t(value, *args, _force_type=True, _nodes_cache=_nodes_cache, _cache_nodes=True, _force_new=_deep_new, _deep_new=_deep_new, _copy_guard=True, **kwargs)

        if cls is ConfigNode and not _force_type:
            # deduce type and call it recursively (this time enforcing it)
            if not has_value:
                raise ValueError('Cannot deduce target type without a positional argument - deduction is always done w.r.t. the first argument')
            from .dict import ConfigDict
            from .list import ConfigList
            from .tuple import ConfigTuple
            from .scalar import ConfigScalar

            if isinstance(value, collections.Sequence) and not isinstance(value, str) and not isinstance(value, bytes):
                if isinstance(value, collections.MutableSequence):
                    t = ConfigList
                else:
                    t = ConfigTuple
            elif isinstance(value, collections.MutableMapping):
                t = ConfigDict
            else:
                t = ConfigScalar

            return t(value, *args, _force_type=True, _nodes_cache=_nodes_cache, _cache_nodes=True, _force_new=_force_new, _deep_new=_deep_new, **kwargs)
        
        from .composed import ComposedNode
        if issubclass(cls, ComposedNode):
            kwargs['_nodes_cache'] = _nodes_cache
            kwargs['_cache_nodes'] = _cache_nodes
            kwargs['_force_new'] = _force_new
            kwargs['_deep_new'] = _deep_new

        if has_value:
            ret = super().__call__(value, *args, **kwargs)
        else:
            ret = super().__call__(*args, **kwargs)

        if has_value and _cache_nodes and _nodes_cache is not None:
            _nodes_cache[persistent_id(value)] = ret
 
        return ret


class ConfigNode(metaclass=ConfigNodeMeta):
    WEAK = -1
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

        self._default_merge_mode = 0
        self._default_delete = False

    def __repr__(self, simple=False):
        return f'<Object {type(self).__name__!r} at 0x{id(self):02x}>'

    class yamlfigns(Namespace):
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
            return self.yamlfigns.merge_mode == ConfigNode.WEAK

        @property
        def force(self):
            return self.yamlfigns.merge_mode == ConfigNode.FORCE

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

        @value.setter
        def value(self, value):
            return self._set_value(value)

        @staticproperty
        @staticmethod
        def tag():
            return None

        def has_priority_over(self, other, if_equal=False):
            if self.yamlfigns.merge_mode == other.yamlfigns.merge_mode:
                return if_equal
            return self.yamlfigns.merge_mode > other.yamlfigns.merge_mode

        def preprocess(self, builder):
            return self.yamlfigns.on_preprocess([], builder)

        def on_preprocess(self, path, builder):
            return self

        def premerge(self, into=None):
            return self.yamlfigns.on_premerge([], into)

        def on_premerge(self, path, into):
            return self

        def evaluate(self):
            return self.yamlfigns.evaluate_node([], self)

        def evaluate_node(self, path, root):
            evaluated = self.yamlfigns.on_evaluate(path, root)
            assert evaluated is not self
            assert not isinstance(evaluated, ConfigNode)
            return evaluated

        def on_evaluate(self, path, ctx):
            return self.yamlfigns.value

        def copy(self):
            return ConfigNode(self, _force_new=True, _deep_new=False)#, # pylint: disable=unexpected-keyword-arg,redundant-keyword-arg
                #idx=self._idx,
                #merge_mode=self._merge_mode,
                #delete=self._delete,
                #metadata=self._metadata,
                #source_file=self._source_file) 

        def deepcopy(self):
            return ConfigNode(self, _force_new=True, _deep_new=True) #, # pylint: disable=unexpected-keyword-arg,redundant-keyword-arg
                #idx=self._idx,
                #merge_mode=self._merge_mode,
                #delete=self._delete,
                #metadata=self._metadata,
                #source_file=self._source_file)

        def get_node_info(self):
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
            return self.yamlfigns.tag, self.yamlfigns.get_node_info(), self.yamlfigns.value
